import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# KONFIGURASI HALAMAN & GAYA
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Monitoring Proyek RKP",
    page_icon="🌴",
    layout="wide",
    initial_sidebar_state="expanded",
)

COLOR_TARGET = "#6E9B79"
COLOR_REALISASI = "#E8A33D"
COLOR_BG = "#121D16"
COLOR_PANEL = "#1B2B21"
COLOR_GOOD = "#6FBF8B"
COLOR_WARN = "#E8A33D"
COLOR_BAD = "#E2705F"
COLOR_MUTED = "#9DB3A4"

DATA_DEFAULT = Path(__file__).parent / "data" / "rkp_data.csv"

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

      html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }
      .disp { font-family: 'Space Grotesk', sans-serif; }
      .mono { font-family: 'IBM Plex Mono', monospace; }

      [data-testid="stMetric"] {
          background: rgba(255,255,255,0.035);
          border: 1px solid rgba(255,255,255,0.09);
          border-radius: 12px;
          padding: 14px 16px 10px;
      }
      [data-testid="stMetricLabel"] {
          font-family: 'IBM Plex Mono', monospace;
          font-size: 11px !important;
          letter-spacing: 0.5px;
          color: #9DB3A4 !important;
          text-transform: uppercase;
      }
      [data-testid="stMetricValue"] {
          font-family: 'Space Grotesk', sans-serif;
      }
      .status-pill {
          display: inline-block; padding: 3px 10px; border-radius: 20px;
          font-family: 'Space Grotesk', sans-serif; font-size: 11px; font-weight: 600;
      }
      .eyebrow {
          font-family: 'IBM Plex Mono', monospace; font-size: 12px; letter-spacing: 2px;
          color: #E8A33D; margin-bottom: 6px;
      }
      section[data-testid="stSidebar"] { border-right: 1px solid rgba(255,255,255,0.08); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# PEMUATAN & PEMBERSIHAN DATA
# ---------------------------------------------------------------------------

FIXED_COLUMNS = {
    "PT": "pt",
    "Proyek": "proyek",
    "Tahun": "tahun",
    "Kegiatan": "kegiatan",
    "Sub Kegiatan": "sub_kegiatan",
    "Rincian Kegiatan": "rincian",
    "Total Hektar": "total_hektar",
    "(Ha/Pkk/Mtr)1": "satuan_rencana",
    "(Ha/Pkk/Mtr)": "satuan_target",
    "Target Biaya": "target_biaya",
    "Target Rp/(Ha/Pkk/Mtr)": "target_rp_satuan",
    "Total Target Rp/Ha": "total_target_rp_ha",
    "Target Rp/Ha (Realisasi)": "target_rp_ha_realisasi",
    "Realisasi Rp/Ha": "realisasi_rp_ha",
    "Capaian Fisik": "capaian_fisik",
    "Capaian Biaya": "capaian_biaya",
}


@st.cache_data(show_spinner=False)
def load_default_data():
    df = pd.read_csv(DATA_DEFAULT)
    return df, "April"


def parse_uploaded_excel(file):
    """Baca file xlsx dengan format sama seperti Update_Rekap_RKP_1.xlsx.
    Kolom 'Realisasi Biaya <Bulan>' / 'Realisasi Fisik <Bulan>' dideteksi
    otomatis sehingga bulan laporan bisa berubah tanpa mengubah kode."""
    sheet = "Rekap Proyek"
    xls = pd.ExcelFile(file)
    if sheet not in xls.sheet_names:
        sheet = xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=sheet)
    df = df.dropna(how="all")

    rename_map = {}
    bulan_label = None
    for col in df.columns:
        col_str = str(col).strip()
        if col_str in FIXED_COLUMNS:
            rename_map[col] = FIXED_COLUMNS[col_str]
        elif col_str.startswith("Realisasi Biaya"):
            rename_map[col] = "realisasi_biaya"
            bulan_label = col_str.replace("Realisasi Biaya", "").strip() or bulan_label
        elif col_str.startswith("Realisasi Fisik"):
            rename_map[col] = "realisasi_fisik"
            bulan_label = col_str.replace("Realisasi Fisik", "").strip() or bulan_label

    df = df.rename(columns=rename_map)
    needed = list(FIXED_COLUMNS.values()) + ["realisasi_biaya", "realisasi_fisik"]
    for c in needed:
        if c not in df.columns:
            df[c] = pd.NA
    df = df[needed]
    df["tahun"] = pd.to_numeric(df["tahun"], errors="coerce").astype("Int64")
    return df, (bulan_label or "tidak diketahui")


def status_of(row):
    cf = row["capaian_fisik"]
    if pd.isna(row["realisasi_biaya"]) and pd.isna(cf):
        return "belum-mulai"
    if pd.isna(cf):
        return "belum-mulai"
    if cf >= 95:
        return "selesai"
    if cf >= 50:
        return "berjalan"
    return "perhatian"


STATUS_META = {
    "belum-mulai": ("Belum Berjalan", COLOR_MUTED, "rgba(157,179,164,0.15)"),
    "berjalan": ("Berjalan", COLOR_WARN, "rgba(232,163,61,0.18)"),
    "selesai": ("Selesai / Sesuai", COLOR_GOOD, "rgba(111,191,139,0.18)"),
    "perhatian": ("Perlu Perhatian", COLOR_BAD, "rgba(226,112,95,0.18)"),
}


def fmt_rp(n, singkat=True):
    if pd.isna(n):
        return "—"
    n = float(n)
    if not singkat:
        return f"Rp {n:,.0f}".replace(",", ".")
    a = abs(n)
    if a >= 1e9:
        return f"Rp {n/1e9:,.2f} M".replace(",", "X").replace(".", ",").replace("X", ".")
    if a >= 1e6:
        return f"Rp {n/1e6:,.1f} Jt".replace(",", "X").replace(".", ",").replace("X", ".")
    if a >= 1e3:
        return f"Rp {n/1e3:,.0f} Rb".replace(",", ".")
    return f"Rp {n:,.0f}".replace(",", ".")


def fmt_pct(n, d=1):
    if pd.isna(n):
        return "—"
    return f"{n:.{d}f}%"


# ---------------------------------------------------------------------------
# SIDEBAR — SUMBER DATA & FILTER
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("<div class='eyebrow'>SUMBER DATA</div>", unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Unggah pembaruan (.xlsx, format sama seperti Update_Rekap_RKP_1.xlsx)",
        type=["xlsx"],
    )

    if uploaded is not None:
        try:
            df, bulan_label = parse_uploaded_excel(uploaded)
            st.success(f"Data terbaru dimuat · periode realisasi: {bulan_label}")
        except Exception as e:
            st.error(f"Gagal membaca file: {e}")
            df, bulan_label = load_default_data()
    else:
        df, bulan_label = load_default_data()
        st.caption("Memakai data bawaan (Update_Rekap_RKP_1.xlsx).")

    st.markdown("---")
    st.markdown("<div class='eyebrow'>FILTER</div>", unsafe_allow_html=True)

    daftar_pt = ["Semua PT"] + sorted(df["pt"].dropna().unique().tolist())
    pt_pilih = st.selectbox("PT", daftar_pt)

    df_scope_pt = df if pt_pilih == "Semua PT" else df[df["pt"] == pt_pilih]
    daftar_proyek = ["Semua Proyek"] + sorted(df_scope_pt["proyek"].dropna().unique().tolist())
    proyek_pilih = st.selectbox("Proyek", daftar_proyek)

    tahun_valid = sorted(df["tahun"].dropna().unique().tolist())
    tahun_dengan_realisasi = sorted(df.loc[df["realisasi_biaya"].notna(), "tahun"].dropna().unique().tolist())
    default_tahun = tahun_dengan_realisasi[-1] if tahun_dengan_realisasi else (tahun_valid[0] if tahun_valid else None)
    opsi_tahun = ["Semua Tahun"] + tahun_valid
    idx_default = opsi_tahun.index(default_tahun) if default_tahun in opsi_tahun else 0
    tahun_pilih = st.selectbox("Tahun", opsi_tahun, index=idx_default)

    daftar_kegiatan = ["Semua Kegiatan"] + sorted(df["kegiatan"].dropna().unique().tolist())
    kegiatan_pilih = st.selectbox("Kegiatan", daftar_kegiatan)

    cari = st.text_input("Cari rincian pekerjaan", "")
    hanya_berjalan = st.checkbox("Hanya yang sudah berjalan", value=False)

# ---------------------------------------------------------------------------
# PENERAPAN FILTER
# ---------------------------------------------------------------------------

f = df.copy()
if pt_pilih != "Semua PT":
    f = f[f["pt"] == pt_pilih]
if proyek_pilih != "Semua Proyek":
    f = f[f["proyek"] == proyek_pilih]
if tahun_pilih != "Semua Tahun":
    f = f[f["tahun"] == tahun_pilih]
if kegiatan_pilih != "Semua Kegiatan":
    f = f[f["kegiatan"] == kegiatan_pilih]
if hanya_berjalan:
    f = f[f["realisasi_biaya"].notna()]
if cari.strip():
    q = cari.strip().lower()
    mask = (
        f["rincian"].fillna("").str.lower().str.contains(q)
        | f["sub_kegiatan"].fillna("").str.lower().str.contains(q)
        | f["kegiatan"].fillna("").str.lower().str.contains(q)
    )
    f = f[mask]

# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------

st.markdown(
    "<div class='eyebrow'>LAPORAN MONITORING PROYEK · RENCANA KERJA PERUSAHAAN (RKP)</div>",
    unsafe_allow_html=True,
)
st.markdown("## 🌴 Dashboard Rekap Proyek Replanting & Reklamasi")
st.caption(
    f"{len(df):,}".replace(",", ".")
    + f" baris rincian pekerjaan · realisasi tersedia s.d. periode **{bulan_label}** · "
    + f"{len(f):,}".replace(",", ".")
    + " baris sesuai filter aktif"
)

# ---------------------------------------------------------------------------
# KPI
# ---------------------------------------------------------------------------

total_target = f["target_biaya"].sum()
total_realisasi = f["realisasi_biaya"].sum()
capaian_biaya_overall = (total_realisasi / total_target * 100) if total_target else None

bobot_fisik = (f["target_biaya"].fillna(0) * f["capaian_fisik"].fillna(0)).sum()
capaian_fisik_overall = (bobot_fisik / total_target) if total_target else None

jumlah_item = len(f)
sudah_berjalan = f["realisasi_biaya"].notna().sum()
perlu_perhatian = f.apply(status_of, axis=1).eq("perhatian").sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Realisasi Biaya", fmt_rp(total_realisasi), f"dari target {fmt_rp(total_target)}")
c2.metric(
    "Progres Fisik Tertimbang",
    fmt_pct(capaian_fisik_overall) if capaian_fisik_overall is not None else "—",
    "thd nilai target biaya",
)
c3.metric("Item Pekerjaan", f"{jumlah_item}", f"{sudah_berjalan} sudah berjalan")
c4.metric("Perlu Perhatian", f"{perlu_perhatian}", "capaian fisik < 50%", delta_color="inverse")

st.write("")

# ---------------------------------------------------------------------------
# GRAFIK
# ---------------------------------------------------------------------------

col_a, col_b = st.columns([1.3, 1])

with col_a:
    st.markdown("##### Target vs Realisasi Biaya per Kegiatan")
    grp = (
        f.groupby("kegiatan", as_index=False)[["target_biaya", "realisasi_biaya"]]
        .sum()
        .sort_values("target_biaya", ascending=False)
    )
    grp = grp[grp["target_biaya"] > 0]
    if grp.empty:
        st.info("Tidak ada data untuk filter ini.")
    else:
        fig = go.Figure()
        fig.add_bar(x=grp["kegiatan"], y=grp["target_biaya"], name="Target", marker_color=COLOR_TARGET)
        fig.add_bar(x=grp["kegiatan"], y=grp["realisasi_biaya"], name="Realisasi", marker_color=COLOR_REALISASI)
        fig.update_layout(
            barmode="group",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="IBM Plex Mono, monospace", color=COLOR_MUTED, size=11),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=10, r=10, t=30, b=10),
            height=340,
            yaxis=dict(tickformat=",.2s", gridcolor="rgba(255,255,255,0.06)"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
        )
        st.plotly_chart(fig, width='stretch')

with col_b:
    st.markdown("##### Capaian Fisik per Sub Kegiatan (Top 10)")
    grp2 = f.copy()
    grp2["w"] = grp2["target_biaya"].fillna(0)
    grp2["wc"] = grp2["w"] * grp2["capaian_fisik"].fillna(0)
    sub = grp2.groupby("sub_kegiatan", as_index=False)[["w", "wc"]].sum()
    sub = sub[sub["w"] > 0]
    sub["capaian"] = (sub["wc"] / sub["w"]).round(1)
    sub = sub.sort_values("capaian", ascending=True).tail(10)
    if sub.empty:
        st.info("Tidak ada data untuk filter ini.")
    else:
        colors = [COLOR_GOOD if v >= 90 else COLOR_WARN if v >= 50 else COLOR_BAD for v in sub["capaian"]]
        fig2 = go.Figure(
            go.Bar(
                x=sub["capaian"],
                y=sub["sub_kegiatan"],
                orientation="h",
                marker_color=colors,
                text=[f"{v:.1f}%" for v in sub["capaian"]],
                textposition="outside",
            )
        )
        fig2.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="IBM Plex Mono, monospace", color=COLOR_MUTED, size=11),
            margin=dict(l=10, r=30, t=20, b=10),
            height=340,
            xaxis=dict(range=[0, 100], gridcolor="rgba(255,255,255,0.06)", ticksuffix="%"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.0)"),
            showlegend=False,
        )
        st.plotly_chart(fig2, width='stretch')

st.write("")

# ---------------------------------------------------------------------------
# TABEL RINCIAN
# ---------------------------------------------------------------------------

st.markdown("##### Rincian Pekerjaan & Capaian")

tbl = f.copy()
tbl["status"] = tbl.apply(status_of, axis=1)
tbl["_urut_mulai"] = tbl["realisasi_biaya"].notna()
tbl = tbl.sort_values(
    by=["_urut_mulai", "capaian_fisik", "target_biaya"],
    ascending=[False, True, False],
)

tampil = tbl[
    [
        "pt", "proyek", "tahun", "kegiatan", "sub_kegiatan", "rincian",
        "target_biaya", "realisasi_biaya", "capaian_biaya", "capaian_fisik", "status",
    ]
].rename(
    columns={
        "pt": "PT",
        "proyek": "Proyek",
        "tahun": "Tahun",
        "kegiatan": "Kegiatan",
        "sub_kegiatan": "Sub Kegiatan",
        "rincian": "Rincian Pekerjaan",
        "target_biaya": "Target Biaya (Rp)",
        "realisasi_biaya": "Realisasi Biaya (Rp)",
        "capaian_biaya": "Capaian Biaya (%)",
        "capaian_fisik": "Capaian Fisik (%)",
        "status": "Status",
    }
)
tampil["Status"] = tampil["Status"].map(lambda s: STATUS_META[s][0])

st.dataframe(
    tampil,
    width='stretch',
    height=520,
    hide_index=True,
    column_config={
        "Target Biaya (Rp)": st.column_config.NumberColumn(format="Rp %d"),
        "Realisasi Biaya (Rp)": st.column_config.NumberColumn(format="Rp %d"),
        "Capaian Biaya (%)": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
        "Capaian Fisik (%)": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
    },
)

st.caption(
    f"Menampilkan {len(tampil):,}".replace(",", ".")
    + " baris sesuai filter. Unggah file pembaruan bulan berikutnya lewat panel kiri "
    + "untuk memperbarui seluruh dashboard tanpa perlu deploy ulang."
)

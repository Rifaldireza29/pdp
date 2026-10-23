from datetime import date, datetime, timedelta, timezone
import os
import urllib.parse
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import streamlit as st

# Konfigurasi halaman
st.set_page_config(
    page_title="PDP & Campaign Content Planner", page_icon="🛍️", layout="wide"
)

# Tambahan CSS agar card lebih rapi dan tombol aksi muat sempurna
st.markdown(
    """
    <style>
    .stButton button {
        width: 100%;
        padding: 4px 8px;
        font-size: 14px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Konfigurasi Akses Google Sheets via st.secrets
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_gspread_client():
  creds_dict = dict(st.secrets["gcp_service_account"])
  creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
  client = gspread.authorize(creds)
  return client


# Fungsi untuk memuat seluruh data dari satu sheet utama
def load_database():
  try:
    client = get_gspread_client()
    sheet = client.open("Content Database Sosmed").sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    expected_columns = [
        "NO",
        "MARKETPLACE",
        "TANGGAL BUAT",
        "CAMPAIGN NAME",
        "UKURAN BANNER",
        "PRODUCT SHOW BANNER",
        "CONTOH/REFERENSI BANNER",
        "LINK DRIVE",
        "CATATAN",
        "STATUS",
    ]

    if df.empty:
      df = pd.DataFrame(columns=expected_columns)
    else:
      for col in expected_columns:
        if col not in df.columns:
          df[col] = ""
      if "UKURAN BANNER" in df.columns:
        df["UKURAN BANNER"] = df["UKURAN BANNER"].apply(
            lambda x: x.split(", ") if isinstance(x, str) and x else []
        )
    return df
  except Exception as e:
    return pd.DataFrame(
        columns=[
            "NO",
            "MARKETPLACE",
            "TANGGAL BUAT",
            "CAMPAIGN NAME",
            "UKURAN BANNER",
            "PRODUCT SHOW BANNER",
            "CONTOH/REFERENSI BANNER",
            "LINK DRIVE",
            "CATATAN",
            "STATUS",
        ]
    )


# Fungsi untuk menyimpan seluruh DataFrame ke Google Sheets
def save_database(df):
  try:
    client = get_gspread_client()
    sheet = client.open("Content Database Sosmed").sheet1

    df_to_save = df.copy()
    if "UKURAN BANNER" in df_to_save.columns:
      df_to_save["UKURAN BANNER"] = df_to_save["UKURAN BANNER"].apply(
          lambda x: ", ".join(x) if isinstance(x, list) else str(x)
      )

    sheet.clear()
    header = list(df_to_save.columns)
    rows = df_to_save.values.tolist()
    sheet.update(range_name="A1", values=[header] + rows)
  except Exception as e:
    if "<Response [200]>" not in str(e):
      st.error(f"Gagal menyimpan ke Google Sheets: {e}")


st.title("🛍️ PDP & Campaign Content Planner")
st.markdown(
    "Kelola seluruh campaign banner Shopee & Tokopedia dalam satu laporan"
    " terpadu."
)

# Inisialisasi Session State
if "content_db" not in st.session_state:
  st.session_state["content_db"] = load_database()

# Sidebar Navigasi Menu
st.sidebar.title("📌 Navigasi Menu")
menu = st.sidebar.radio(
    "Pilih Menu:",
    [
        "📋 Daftar Campaign & Banner",
        "➕ Tambah Campaign Baru",
        "👔 Approval / Status Checker",
        "📊 Rekapan & Statistik",
    ],
)

# Folder lokal untuk menyimpan gambar upload sementara
UPLOAD_DIR = "uploaded_banners"
if not os.path.exists(UPLOAD_DIR):
  os.makedirs(UPLOAD_DIR)

# ==========================================
# MENU 1: DAFTAR CAMPAIGN & BANNER
# ==========================================
if menu == "📋 Daftar Campaign & Banner":
  col_title, col_btn = st.columns([4, 1])
  with col_title:
    st.subheader("📋 Tabel Manajemen Seluruh Campaign & Banner")
  with col_btn:
    if st.button("🔄 Refresh Data", key="ref_menu1"):
      st.session_state["content_db"] = load_database()
      st.success("Data berhasil diperbarui dari Google Sheets!")
      st.rerun()

  df = st.session_state["content_db"]

  if df.empty:
    st.info(
        "Belum ada data campaign. Silakan tambah melalui menu **Tambah Campaign"
        " Baru**."
    )
  else:
    st.markdown("### 🔍 Filter & Pencarian Data")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
      filter_market = st.selectbox(
          "Filter Marketplace", ["Semua", "Shopee", "Tokopedia"]
      )
    with col_f2:
      filter_status = st.selectbox(
          "Filter Status", ["Semua", "Draft", "Pending", "Done"]
      )
    with col_f3:
      filter_tanggal = st.date_input(
          "📅 Filter Tanggal", value=None, key="filter_tgl_buat"
      )
    with col_f4:
      search_query = st.text_input(
          "🔍 Cari Campaign Name / SKU", placeholder="Ketik kata kunci..."
      )

    filtered_df = df.copy()

    if filter_market != "Semua":
      filtered_df = filtered_df[
          filtered_df["MARKETPLACE"].str.lower() == filter_market.lower()
      ]

    if filter_status != "Semua":
      filtered_df = filtered_df[
          filtered_df["STATUS"].str.lower() == filter_status.lower()
      ]

    if filter_tanggal:
      tgl_str = filter_tanggal.strftime("%Y-%m-%d")
      filtered_df = filtered_df[
          filtered_df["TANGGAL BUAT"].astype(str).str.startswith(tgl_str)
      ]

    if search_query:
      filtered_df = filtered_df[
          filtered_df["CAMPAIGN NAME"]
          .str.contains(search_query, case=False, na=False)
          | filtered_df["PRODUCT SHOW BANNER"]
          .str.contains(search_query, case=False, na=False)
      ]

    st.markdown("---")

    if filtered_df.empty:
      st.warning(
          "Tidak ada data campaign yang cocok dengan filter / pencarian tersebut."
      )
    else:
      st.markdown(
          "💡 **Panduan:** Pilih status langsung pada dropdown di setiap baris"
          " untuk mengubahnya, atau gunakan tombol **✏️ Edit** / **🗑️ Hapus**."
      )

      for index, row in filtered_df.iterrows():
        uk_str = (
            ", ".join(row["UKURAN BANNER"])
            if isinstance(row["UKURAN BANNER"], list)
            else str(row["UKURAN BANNER"])
        )

        with st.container(border=True):
          c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = st.columns(
              [0.4, 0.8, 0.9, 1.2, 1.0, 0.9, 0.9, 0.8, 1.1, 0.9]
          )

          with c1:
            st.markdown(f"📌 **{row['NO']}**")

          with c2:
            st.markdown("🛒 **Market:**")
            st.write(f"**{row['MARKETPLACE']}**")

          with c3:
            st.markdown("📅 **Dibuat:**")
            st.write(
                str(row["TANGGAL BUAT"])
                if pd.notna(row["TANGGAL BUAT"])
                else "-"
            )

          with c4:
            st.markdown("🏷️ **Campaign:**")
            c_name_short = (
                str(row["CAMPAIGN NAME"])[:20] + "..."
                if len(str(row["CAMPAIGN NAME"])) > 20
                else str(row["CAMPAIGN NAME"])
            )
            with st.popover("📄 Detail"):
              st.text_area(
                  "Campaign Name",
                  value=str(row["CAMPAIGN NAME"]),
                  height=120,
                  disabled=True,
                  label_visibility="collapsed",
              )
            st.write(c_name_short)

          with c5:
            st.markdown("🖼️ **Ref:**")
            img_path = str(row["CONTOH/REFERENSI BANNER"])
            if img_path and os.path.exists(img_path):
              st.image(img_path, width=50)
            else:
              st.write("-")

          with c6:
            st.markdown("📐 **Ukuran:**")
            st.write(uk_str if uk_str else "-")

          with c7:
            st.markdown("📦 **Product:**")
            prod_val = str(row["PRODUCT SHOW BANNER"])
            if "http" in prod_val:
              st.markdown(f"[Link]({prod_val})")
            else:
              sku_short = (
                  prod_val[:10] + "..." if len(prod_val) > 10 else prod_val
              )
              with st.popover("📦 SKU"):
                st.text_area(
                    "Product Show",
                    value=prod_val,
                    height=90,
                    disabled=True,
                    label_visibility="collapsed",
                )
              st.write(sku_short if sku_short else "-")

          with c8:
            st.markdown("🔗 **Drive:**")
            drive_val = str(row["LINK DRIVE"])
            if drive_val.startswith("http"):
              st.markdown(f"[Buka]({drive_val})")
            else:
              st.write("-")

          with c9:
            st.markdown("📊 **Status:**")
            status_options = ["Draft", "Pending", "Done"]
            current_status = (
                row["STATUS"] if row["STATUS"] in status_options else "Draft"
            )
            widget_key = f"status_inline_{row['NO']}_{index}"

            def update_status_inline(r_idx=index, w_key=widget_key):
              new_val = st.session_state[w_key]
              st.session_state["content_db"].loc[r_idx, "STATUS"] = new_val
              save_database(st.session_state["content_db"])

            st.selectbox(
                "Status",
                status_options,
                index=status_options.index(current_status),
                key=widget_key,
                on_change=update_status_inline,
                label_visibility="collapsed",
            )

            catatan_txt = (
                str(row["CATATAN"])
                if pd.notna(row["CATATAN"]) and row["CATATAN"] != ""
                else "-"
            )
            if catatan_txt != "-":
              with st.popover("📝 Catatan"):
                st.write(catatan_txt)

          with c10:
            st.markdown("⚡ **Aksi:**")
            col_e, col_d = st.columns(2)
            with col_e:
              if st.button("✏️", key=f"edit_row_{index}", help="Edit"):
                st.session_state["edit_index"] = index
                st.rerun()
            with col_d:
              if st.button("🗑️", key=f"del_row_{index}", help="Hapus"):
                st.session_state["content_db"] = (
                    st.session_state["content_db"].drop(index).reset_index(drop=True)
                )
                st.session_state["content_db"]["NO"] = range(
                    1, len(st.session_state["content_db"]) + 1
                )
                save_database(st.session_state["content_db"])
                st.success("Data berhasil dihapus!")
                st.rerun()

      if "edit_index" in st.session_state:
        e_idx = st.session_state["edit_index"]
        if e_idx in st.session_state["content_db"].index:
          r_data = st.session_state["content_db"].loc[e_idx]
          st.markdown("---")
          st.subheader(f"✏️ Edit Data Baris No. {r_data['NO']}")

          with st.form("form_edit_campaign"):
            edit_market = st.selectbox(
                "Marketplace",
                ["Shopee", "Tokopedia"],
                index=(
                    0
                    if str(r_data["MARKETPLACE"]).lower() == "shopee"
                    else 1
                ),
            )
            edit_tgl_buat = st.date_input(
                "Tanggal Pembuatan",
                value=(
                    datetime.strptime(str(r_data["TANGGAL BUAT"]), "%Y-%m-%d").date()
                    if pd.notna(r_data["TANGGAL BUAT"])
                    and str(r_data["TANGGAL BUAT"]) != ""
                    else date.today()
                ),
            )
            edit_camp_name = st.text_area(
                "Campaign Name (Judul, Periode, Promo, CTA)",
                value=str(r_data["CAMPAIGN NAME"]),
                height=120,
            )
            ec1, ec2 = st.columns(2)
            with ec1:
              curr_ukuran = r_data["UKURAN BANNER"]
              if isinstance(curr_ukuran, str):
                curr_ukuran = (
                    [i.strip() for i in curr_ukuran.split(",")]
                    if curr_ukuran
                    else []
                )
              edit_ukuran = st.multiselect(
                  "Ukuran Banner",
                  ["Feed 1:1", "IGS", "Banner"],
                  default=[
                      u for u in curr_ukuran if u in ["Feed 1:1", "IGS", "Banner"]
                  ],
              )
              edit_product = st.text_area(
                  "Product Show Banner (SKU atau Link Produk)",
                  value=str(r_data["PRODUCT SHOW BANNER"]),
                  height=90,
              )
            with ec2:
              edit_link_drive = st.text_input(
                  "Link Drive", value=str(r_data["LINK DRIVE"])
              )
              status_list = ["Draft", "Pending", "Done"]
              s_idx = (
                  status_list.index(r_data["STATUS"])
                  if r_data["STATUS"] in status_list
                  else 0
              )
              edit_status = st.selectbox("Status", status_list, index=s_idx)

            edit_referensi = st.text_input(
                "Path / Keterangan Contoh Referensi Gambar",
                value=str(r_data["CONTOH/REFERENSI BANNER"]),
            )
            edit_catatan = st.text_area(
                "Catatan Tambahan", value=str(r_data["CATATAN"])
            )

            col_sub1, col_sub2 = st.columns(2)
            with col_sub1:
              btn_update = st.form_submit_button(
                  "💾 Update Perubahan", type="primary"
              )
            with col_sub2:
              btn_cancel = st.form_submit_button("❌ Batal")

            if btn_update:
              db_df = st.session_state["content_db"]
              db_df.loc[e_idx, "MARKETPLACE"] = edit_market
              db_df.loc[e_idx, "TANGGAL BUAT"] = edit_tgl_buat.strftime(
                  "%Y-%m-%d"
              )
              db_df.loc[e_idx, "CAMPAIGN NAME"] = edit_camp_name
              db_df.loc[e_idx, "UKURAN BANNER"] = edit_ukuran
              db_df.loc[e_idx, "PRODUCT SHOW BANNER"] = edit_product
              db_df.loc[e_idx, "LINK DRIVE"] = edit_link_drive
              db_df.loc[e_idx, "STATUS"] = edit_status
              db_df.loc[e_idx, "CONTOH/REFERENSI BANNER"] = edit_referensi
              db_df.loc[e_idx, "CATATAN"] = edit_catatan

              save_database(db_df)
              del st.session_state["edit_index"]
              st.success("Perubahan berhasil disimpan ke Google Sheets!")
              st.rerun()

            if btn_cancel:
              del st.session_state["edit_index"]
              st.rerun()

# ==========================================
# MENU 2: TAMBAH CAMPAIGN BARU
# ==========================================
elif menu == "➕ Tambah Campaign Baru":
  st.subheader("➕ Tambah Baris Campaign Baru ke Laporan Utama")

  with st.form("form_tambah_campaign", clear_on_submit=True):
    marketplace_pilihan = st.selectbox(
        "Pilih Marketplace / Platform", ["Shopee", "Tokopedia"]
    )
    tanggal_buat = st.date_input("Tanggal Pembuatan", value=date.today())
    camp_name = st.text_area(
        "Campaign Name (Judul, Periode, Promo, Hadiah, CTA)"
    )

    col1, col2 = st.columns(2)
    with col1:
      ukuran_banner = st.multiselect(
          "Ukuran Banner", ["Feed 1:1", "IGS", "Banner"]
      )
      product_show = st.text_area(
          "Product Show Banner (Daftar SKU / Link Produk)"
      )
    with col2:
      link_drive = st.text_input("Link Drive")
      status = st.selectbox("Status", ["Draft", "Pending", "Done"], index=0)

    uploaded_file = st.file_uploader(
        "Upload Contoh / Referensi Banner (Gambar)",
        type=["png", "jpg", "jpeg"],
    )
    catatan = st.text_area("Catatan Tambahan")

    submit_button = st.form_submit_button("Simpan ke Google Sheets")

    if submit_button:
      if camp_name:
        st.session_state["content_db"] = load_database()
        current_len = len(st.session_state["content_db"])
        new_no = current_len + 1

        ref_path = ""
        if uploaded_file is not None:
          ref_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
          with open(ref_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        new_data = {
            "NO": new_no,
            "MARKETPLACE": marketplace_pilihan,
            "TANGGAL BUAT": tanggal_buat.strftime("%Y-%m-%d"),
            "CAMPAIGN NAME": camp_name,
            "UKURAN BANNER": ukuran_banner,
            "PRODUCT SHOW BANNER": product_show,
            "CONTOH/REFERENSI BANNER": ref_path,
            "LINK DRIVE": link_drive,
            "CATATAN": catatan,
            "STATUS": status,
        }

        st.session_state["content_db"] = pd.concat(
            [
                st.session_state["content_db"],
                pd.DataFrame([new_data]),
            ],
            ignore_index=True,
        )
        save_database(st.session_state["content_db"])
        st.success(
            "Berhasil! Campaign baru tersimpan ke Laporan Utama Google Sheets."
        )
      else:
        st.warning("Mohon setidaknya isi kolom **Campaign Name**.")

# ==========================================
# MENU 3: APPROVAL / STATUS CHECKER
# ==========================================
elif menu == "👔 Approval / Status Checker":
  col_title_app, col_btn_app = st.columns([4, 1])
  with col_title_app:
    st.subheader("👔 Panel Approval Campaign & WhatsApp Reminder")
  with col_btn_app:
    if st.button("🔄 Refresh Data", key="ref_menu3"):
      st.session_state["content_db"] = load_database()
      st.success("Data berhasil diperbarui!")
      st.rerun()

  df = st.session_state["content_db"]

  if df.empty:
    st.info("Belum ada data campaign.")
  else:
    st.markdown("### 📋 Daftar Approval & Aksi Cepat (Semua Marketplace)")

    for index, row in df.iterrows():
      uk_str = (
          ", ".join(row["UKURAN BANNER"])
          if isinstance(row["UKURAN BANNER"], list)
          else str(row["UKURAN BANNER"])
      )

      with st.container(border=True):
        col_info1, col_info2, col_info3, col_info4, col_info5, col_aksi = (
            st.columns([1.2, 1.1, 1.1, 0.9, 0.9, 1.2])
        )

        with col_info1:
          st.markdown(
              f"📌 **No. {row['NO']} | [{row['MARKETPLACE']}]**"
          )
          st.caption(f"Dibuat: {row['TANGGAL BUAT']}")
          c_name_short = (
              str(row["CAMPAIGN NAME"])[:30] + "..."
              if len(str(row["CAMPAIGN NAME"])) > 30
              else str(row["CAMPAIGN NAME"])
          )
          with st.popover("📄 Detail"):
            st.text_area(
                "Campaign Name",
                value=str(row["CAMPAIGN NAME"]),
                height=120,
                disabled=True,
                label_visibility="collapsed",
            )
          st.write(f"🏷️ {c_name_short}")

        with col_info2:
          st.markdown("🖼️ **Referensi:**")
          img_path = str(row["CONTOH/REFERENSI BANNER"])
          if img_path and os.path.exists(img_path):
            st.image(img_path, width=65)
          else:
            st.write("-")

        with col_info3:
          st.markdown("📐 **Ukuran & Status:**")
          st.write(f"Ukuran: {uk_str if uk_str else '-'}")
          st.write(f"Status: **{row['STATUS']}**")

        with col_info4:
          st.markdown("🔗 **Drive:**")
          drive_val = str(row["LINK DRIVE"])
          if drive_val.startswith("http"):
            st.markdown(f"[Buka Link]({drive_val})")
          else:
            st.write("-")

        with col_info5:
          st.markdown("📝 **Catatan:**")
          catatan_txt = (
              str(row["CATATAN"])
              if pd.notna(row["CATATAN"]) and row["CATATAN"] != ""
              else "-"
          )
          if catatan_txt != "-":
            with st.popover("📄 Catatan"):
              st.write(catatan_txt)
          else:
            st.write("-")

        with col_aksi:
          st.markdown("⚡ **Approval:**")
          btn_app, btn_rej = st.columns(2)
          with btn_app:
            if st.button("✅", key=f"app_btn_{index}", help="Approve (Done)"):
              df.loc[index, "STATUS"] = "Done"
              save_database(df)
              st.success("Disetujui (Done)!")
              st.rerun()
          with btn_rej:
            if st.button("❌", key=f"rej_btn_{index}", help="Not Approve (Pending)"):
              df.loc[index, "STATUS"] = "Pending"
              save_database(df)
              st.warning("Diberi status Pending / Revisi.")
              st.rerun()

        with st.expander(
            f"📲 Kirim Reminder WhatsApp untuk No. {row['NO']} ({row['MARKETPLACE']})"
        ):
          daftar_tim = {
              "Pak Reza": "6281321686233",
              "Bu Emma": "628175731188",
              "Pak Gilang": "6281809830066",
              "Surya": "6281945678904",
          }
          pilihan_admin = st.selectbox(
              "Pilih Kontak Tujuan:",
              list(daftar_tim.keys()),
              key=f"sel_tim_{index}",
          )
          nomor_tujuan = st.text_input(
              "Nomor WhatsApp:",
              value=daftar_tim[pilihan_admin],
              key=f"no_wa_{index}",
          )

          pesan_wa = (
              f"Halo *{pilihan_admin}*, mohon bantuannya untuk cek & approve campaign *{row['MARKETPLACE']}* berikut:\n\n"
              f"📌 *No:* {row['NO']}\n"
              f"🏷️ *Campaign:* {row['CAMPAIGN NAME']}\n"
              f"📐 *Ukuran:* {uk_str}\n"
              f"📊 *Status Saat Ini:* {row['STATUS']}\n"
              f"🔗 *Link Drive:* {row['LINK DRIVE']}\n\n"
              f"Terima kasih!"
          )

          encoded_pesan = urllib.parse.quote(pesan_wa)
          whatsapp_url = f"https://api.whatsapp.com/send?phone={nomor_tujuan}&text={encoded_pesan}"

          st.markdown(
              f'<a href="{whatsapp_url}" target="_blank"><button'
              ' style="background-color:#25D366; color:white; padding:8px'
              ' 16px; border:none; border-radius:5px; cursor:pointer;'
              ' font-size:14px;">📲 Kirim WhatsApp Reminder</button></a>',
              unsafe_allow_html=True,
          )

# ==========================================
# MENU 4: REKAPAN & STATISTIK
# ==========================================
elif menu == "📊 Rekapan & Statistik":
  col_title_rek, col_btn_rek = st.columns([4, 1])
  with col_title_rek:
    st.subheader("📊 Rekapan & Statistik Keseluruhan Campaign")
  with col_btn_rek:
    if st.button("🔄 Refresh Data", key="ref_menu4"):
      st.session_state["content_db"] = load_database()
      st.success("Data berhasil diperbarui!")
      st.rerun()

  df = st.session_state["content_db"]

  if df.empty:
    st.info("Belum ada data campaign untuk direkap.")
  else:
    st.markdown("### 🔍 Filter & Rekapan Per Bulan")

    df_temp = df.copy()
    df_temp["BULAN"] = df_temp["TANGGAL BUAT"].apply(
        lambda x: str(x)[:7] if pd.notna(x) and len(str(x)) >= 7 else "Lainnya"
    )
    daftar_bulan = ["Semua"] + sorted(
        df_temp["BULAN"].unique().tolist(), reverse=True
    )

    col_rf1, col_rf2 = st.columns(2)
    with col_rf1:
      rek_market = st.selectbox(
          "Filter Marketplace", ["Semua", "Shopee", "Tokopedia"], key="rek_market"
      )
    with col_rf2:
      rek_bulan = st.selectbox(
          "📅 Pilih Bulan (Format: YYYY-MM)", daftar_bulan, key="rek_bulan"
      )

    recap_filtered = df.copy()

    if rek_market != "Semua":
      recap_filtered = recap_filtered[
          recap_filtered["MARKETPLACE"].str.lower() == rek_market.lower()
      ]

    if rek_bulan != "Semua":
      recap_filtered = recap_filtered[
          recap_filtered["TANGGAL BUAT"].astype(str).str.startswith(rek_bulan)
      ]

    total_campaign = len(recap_filtered)
    total_done = len(
        recap_filtered[recap_filtered["STATUS"].str.lower() == "done"]
    )
    total_pending = len(
        recap_filtered[recap_filtered["STATUS"].str.lower() == "pending"]
    )
    total_draft = len(
        recap_filtered[recap_filtered["STATUS"].str.lower() == "draft"]
    )

    total_shopee = len(
        recap_filtered[recap_filtered["MARKETPLACE"].str.lower() == "shopee"]
    )
    total_tokopedia = len(
        recap_filtered[recap_filtered["MARKETPLACE"].str.lower() == "tokopedia"]
    )

    st.markdown("### 📈 Ringkasan Metrik Utama")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Campaign", total_campaign)
    m2.metric("Status Done", total_done)
    m3.metric("Status Pending", total_pending)
    m4.metric("Status Draft", total_draft)

    st.markdown("<br>", unsafe_allow_html=True)
    m5, m6 = st.columns(2)
    m5.metric("🛒 Total Campaign Shopee", total_shopee)
    m6.metric("🛒 Total Campaign Tokopedia", total_tokopedia)

    st.markdown("---")
    st.markdown("### 📜 Daftar Riwayat Semua Campaign")

    recap_table = recap_filtered[
        [
            "NO",
            "MARKETPLACE",
            "TANGGAL BUAT",
            "CAMPAIGN NAME",
            "STATUS",
            "LINK DRIVE",
        ]
    ].copy()
    recap_table["CAMPAIGN NAME"] = recap_table["CAMPAIGN NAME"].apply(
        lambda x: str(x).replace("\n", " ")
    )

    st.dataframe(recap_table, use_container_width=True, hide_index=True)
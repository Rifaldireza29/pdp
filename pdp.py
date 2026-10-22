from datetime import date, datetime, timedelta, timezone
import urllib.parse
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import streamlit as st

# Konfigurasi halaman
st.set_page_config(
    page_title="PDP & Campaign Content Planner", page_icon="🛍️", layout="wide"
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


# Fungsi untuk memuat data dari Google Sheets ke Pandas DataFrame
def load_database():
  try:
    client = get_gspread_client()
    # Sesuaikan nama sheet/tab di Google Sheets, misal "Shopee" atau "Shopee OP"
    sheet = client.open("Content Database Sosmed").worksheet("Shopee")
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    expected_columns = [
        "NO",
        "CAMPAIGN NAME",
        "UKURAN BANNER",
        "PRODUCT SHOOW BANNER",
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
    return df
  except Exception as e:
    return pd.DataFrame(
        columns=[
            "NO",
            "CAMPAIGN NAME",
            "UKURAN BANNER",
            "PRODUCT SHOOW BANNER",
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
    sheet = client.open("Content Database Sosmed").worksheet("Shopee")

    df_to_save = df.copy()
    sheet.clear()
    header = list(df_to_save.columns)
    rows = df_to_save.values.tolist()
    sheet.update([header] + rows)
  except Exception as e:
    st.error(f"Gagal menyimpan ke Google Sheets: {e}")


# Inisialisasi Session State dengan Google Sheets
if "content_db" not in st.session_state:
  st.session_state["content_db"] = load_database()

st.title("🛍️ PDP & Campaign Content Planner")
st.markdown(
    "Kelola campaign banner, ukuran banner, daftar SKU produk (Product Show),"
    " referensi, link Google Drive, dan status (Terhubung ke Google Sheets)."
)

# Sidebar untuk Navigasi Menu
st.sidebar.title("📌 Navigasi Menu")
menu = st.sidebar.radio(
    "Pilih Menu:",
    [
        "📋 Daftar Campaign & Banner",
        "➕ Tambah Campaign Baru",
        "👔 Approval / Status Checker",
    ],
)

# ==========================================
# MENU 1: DAFTAR CAMPAIGN & BANNER
# ==========================================
if menu == "📋 Daftar Campaign & Banner":
  col_title, col_btn = st.columns([4, 1])
  with col_title:
    st.subheader("📋 Tabel Manajemen Campaign & Banner PDP")
  with col_btn:
    if st.button("🔄 Refresh Data", key="ref_menu1"):
      st.session_state["content_db"] = load_database()
      st.success("Data berhasil diperbarui dari Google Sheets!")
      st.rerun()

  df = st.session_state["content_db"]

  if df.empty:
    st.info(
        "Belum ada data campaign. Silakan tambah melalui menu **Tambah"
        " Campaign Baru**."
    )
  else:
    col_f1, col_f2 = st.columns(2)
    with col_f1:
      filter_status = st.selectbox(
          "Filter Status", ["Semua", "DONE", "PENDING", "DRAFT"]
      )
    with col_f2:
      search_query = st.text_input(
          "🔍 Cari Campaign Name / SKU", placeholder="Ketik kata kunci..."
      )

    filtered_df = df.copy()
    if filter_status != "Semua":
      filtered_df = filtered_df[
          filtered_df["STATUS"].str.upper() == filter_status
      ]

    if search_query:
      filtered_df = filtered_df[
          filtered_df["CAMPAIGN NAME"]
          .str.contains(search_query, case=False, na=False)
          | filtered_df["PRODUCT SHOOW BANNER"]
          .str.contains(search_query, case=False, na=False)
      ]

    if filtered_df.empty:
      st.warning("Tidak ada data yang cocok dengan filter / pencarian.")
    else:
      st.markdown(
          "💡 **Panduan:** Gunakan tombol **✏️ Edit** atau **🗑️ Hapus** di"
          " ujung kanan setiap baris."
      )

      for index, row in filtered_df.iterrows():
        with st.container(border=True):
          c1, c2, c3, c4, c5, c6 = st.columns([1.5, 1.2, 1, 1, 1, 0.8])

          with c1:
            st.markdown(f"📌 **No. {row['NO']}**")
            c_name_short = (
                str(row["CAMPAIGN NAME"])[:60] + "..."
                if len(str(row["CAMPAIGN NAME"])) > 60
                else str(row["CAMPAIGN NAME"])
            )
            with st.popover("📄 Detail Campaign Name"):
              st.text_area(
                  "Campaign Name",
                  value=str(row["CAMPAIGN NAME"]),
                  height=150,
                  disabled=True,
                  label_visibility="collapsed",
              )
            st.write(f"🏷️ {c_name_short}")

          with c2:
            st.markdown("📐 **Ukuran Banner:**")
            st.write(
                str(row["UKURAN BANNER"])
                if pd.notna(row["UKURAN BANNER"])
                else "-"
            )

          with c3:
            st.markdown("📦 **Product Show:**")
            sku_short = (
                str(row["PRODUCT SHOOW BANNER"])[:30] + "..."
                if len(str(row["PRODUCT SHOOW BANNER"])) > 30
                else str(row["PRODUCT SHOOW BANNER"])
            )
            with st.popover("📦 Lihat SKU"):
              st.text_area(
                  "SKU Produk",
                  value=str(row["PRODUCT SHOOW BANNER"]),
                  height=150,
                  disabled=True,
                  label_visibility="collapsed",
              )
            st.write(sku_short)

          with c4:
            st.markdown("🔗 **Link Drive:**")
            if (
                pd.notna(row["LINK DRIVE"])
                and str(row["LINK DRIVE"]).strip() != ""
            ):
              st.markdown(f"[Buka Link]({row['LINK DRIVE']})")
            else:
              st.write("-")

          with c5:
            st.markdown("📊 **Status & Catatan:**")
            st.write(f"Status: **{row['STATUS']}**")
            catatan_txt = (
                str(row["CATATAN"])
                if pd.notna(row["CATATAN"]) and row["CATATAN"] != ""
                else "-"
            )
            if catatan_txt != "-":
              with st.popover("📝 Catatan"):
                st.write(catatan_txt)

          with c6:
            st.markdown("⚡ **Aksi:**")
            col_e, col_d = st.columns(2)
            with col_e:
              if st.button("✏️", key=f"edit_row_{index}", help="Edit Data"):
                st.session_state["edit_index"] = index
                st.rerun()
            with col_d:
              if st.button("🗑️", key=f"del_row_{index}", help="Hapus Data"):
                st.session_state["content_db"] = (
                    st.session_state["content_db"].drop(index).reset_index(drop=True)
                )
                st.session_state["content_db"]["NO"] = range(
                    1, len(st.session_state["content_db"]) + 1
                )
                save_database(st.session_state["content_db"])
                st.success("Data berhasil dihapus!")
                st.rerun()

      # FORM EDIT MUNCUL JIKA TOMBOL EDIT DIKLIK
      if "edit_index" in st.session_state:
        e_idx = st.session_state["edit_index"]
        if e_idx in st.session_state["content_db"].index:
          r_data = st.session_state["content_db"].loc[e_idx]
          st.markdown("---")
          st.subheader(f"✏️ Edit Data Baris No. {r_data['NO']}")

          with st.form("form_edit_campaign"):
            edit_camp_name = st.text_area(
                "Campaign Name (Judul, Periode, Promo, CTA)",
                value=str(r_data["CAMPAIGN NAME"]),
                height=120,
            )
            ec1, ec2 = st.columns(2)
            with ec1:
              edit_ukuran = st.text_input(
                  "Ukuran Banner", value=str(r_data["UKURAN BANNER"])
              )
              edit_sku = st.text_area(
                  "Product Show Banner (Daftar SKU)",
                  value=str(r_data["PRODUCT SHOOW BANNER"]),
                  height=100,
              )
            with ec2:
              edit_link = st.text_input(
                  "Link Drive", value=str(r_data["LINK DRIVE"])
              )
              edit_status = st.selectbox(
                  "Status",
                  ["DONE", "PENDING", "DRAFT"],
                  index=(
                      ["DONE", "PENDING", "DRAFT"].index(
                          str(r_data["STATUS"]).upper()
                      )
                      if str(r_data["STATUS"]).upper()
                      in ["DONE", "PENDING", "DRAFT"]
                      else 0
                  ),
              )

            edit_catatan = st.text_area(
                "Catatan", value=str(r_data["CATATAN"])
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
              db_df.loc[e_idx, "CAMPAIGN NAME"] = edit_camp_name
              db_df.loc[e_idx, "UKURAN BANNER"] = edit_ukuran
              db_df.loc[e_idx, "PRODUCT SHOOW BANNER"] = edit_sku
              db_df.loc[e_idx, "LINK DRIVE"] = edit_link
              db_df.loc[e_idx, "STATUS"] = edit_status
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
  st.subheader("➕ Tambah Baris Campaign Baru ke Google Sheets")

  with st.form("form_tambah_campaign", clear_on_submit=True):
    camp_name = st.text_area(
        "Campaign Name (Judul, Periode, Promo, Hadiah, CTA)"
    )

    col1, col2 = st.columns(2)
    with col1:
      ukuran_banner = st.text_input(
          "Ukuran Banner (Contoh: Feed 1:1, IGS, Banner)"
      )
      product_show = st.text_area(
          "Product Show Banner (Daftar SKU / Produk)"
      )
    with col2:
      link_drive = st.text_input("Link Drive Aset")
      status = st.selectbox("Status", ["PENDING", "DONE", "DRAFT"])

    catatan = st.text_area("Catatan Tambahan")

    submit_button = st.form_submit_button("Simpan ke Google Sheets")

    if submit_button:
      if camp_name:
        st.session_state["content_db"] = load_database()
        current_len = len(st.session_state["content_db"])
        new_no = current_len + 1

        new_data = {
            "NO": new_no,
            "CAMPAIGN NAME": camp_name,
            "UKURAN BANNER": ukuran_banner,
            "PRODUCT SHOOW BANNER": product_show,
            "CONTOH/REFERENSI BANNER": "",
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
        st.success("Berhasil! Campaign baru tersimpan ke Google Sheets.")
      else:
        st.warning("Mohon setidaknya isi kolom **Campaign Name**.")

# ==========================================
# MENU 3: APPROVAL / STATUS CHECKER
# ==========================================
elif menu == "👔 Approval / Status Checker":
  st.subheader("👔 Ringkasan Status Campaign & WhatsApp Reminder")

  df = st.session_state["content_db"]

  if df.empty:
    st.info("Belum ada data.")
  else:
    total_data = len(df)
    total_done = len(df[df["STATUS"].str.upper() == "DONE"])
    total_pending = len(df[df["STATUS"].str.upper() == "PENDING"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Campaign", total_data)
    c2.metric("Status DONE", total_done)
    c3.metric("Status PENDING", total_pending)

    st.markdown("---")
    st.markdown("### 📲 Kirim Pengingat WhatsApp Tim")

    pilihan_camp = st.selectbox(
        "Pilih Campaign:", df["CAMPAIGN NAME"].tolist()
    )
    selected_row = df[df["CAMPAIGN NAME"] == pilihan_camp].iloc[0]

    daftar_tim = {
        "Pak Reza": "6281321686233",
        "Bu Emma": "628175731188",
        "Pak Gilang": "6281809830066",
        "Surya": "6281945678904",
    }

    pilihan_admin = st.selectbox("Pilih Kontak Tujuan:", list(daftar_tim.keys()))
    nomor_tujuan = st.text_input("Nomor WhatsApp:", value=daftar_tim[pilihan_admin])

    pesan_wa = (
        f"Halo *{pilihan_admin}*, mohon bantuannya untuk cek campaign berikut:\n\n"
        f"📌 *Campaign:* {selected_row['CAMPAIGN NAME']}\n"
        f"📐 *Ukuran:* {selected_row['UKURAN BANNER']}\n"
        f"📊 *Status:* {selected_row['STATUS']}\n"
        f"🔗 *Link Drive:* {selected_row['LINK DRIVE']}\n\n"
        f"Terima kasih!"
    )

    encoded_pesan = urllib.parse.quote(pesan_wa)
    whatsapp_url = (
        f"https://api.whatsapp.com/send?phone={nomor_tujuan}&text={encoded_pesan}"
    )

    st.markdown(
        f'<a href="{whatsapp_url}" target="_blank"><button'
        ' style="background-color:#25D366; color:white; padding:10px'
        ' 20px; border:none; border-radius:5px; cursor:pointer; font-size:16px;">📲'
        " Kirim WhatsApp Reminder</button></a>",
        unsafe_allow_html=True,
    )
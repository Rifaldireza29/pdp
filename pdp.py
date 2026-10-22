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


# Fungsi untuk memuat data dari Google Sheets berdasarkan tab yang dipilih
def load_database(worksheet_name):
  try:
    client = get_gspread_client()
    sheet = client.open("Content Database Sosmed").worksheet(worksheet_name)
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
      # Handle Tipe List jika disimpan sebagai string koma
      if "UKURAN BANNER" in df.columns:
        df["UKURAN BANNER"] = df["UKURAN BANNER"].apply(
            lambda x: x.split(", ") if isinstance(x, str) and x else []
        )
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


# Fungsi untuk menyimpan seluruh DataFrame ke Google Sheets pada tab yang aktif
def save_database(df, worksheet_name):
  try:
    client = get_gspread_client()
    sheet = client.open("Content Database Sosmed").worksheet(worksheet_name)

    df_to_save = df.copy()
    if "UKURAN BANNER" in df_to_save.columns:
      df_to_save["UKURAN BANNER"] = df_to_save["UKURAN BANNER"].apply(
          lambda x: ", ".join(x) if isinstance(x, list) else str(x)
      )

    sheet.clear()
    header = list(df_to_save.columns)
    rows = df_to_save.values.tolist()
    sheet.update([header] + rows)
  except Exception as e:
    st.error(f"Gagal menyimpan ke Google Sheets: {e}")


st.title("🛍️ PDP & Campaign Content Planner")
st.markdown(
    "Kelola campaign banner, ukuran banner, daftar SKU/link produk, referensi"
    " gambar, link Drive, dan status."
)

# PILIHAN MARKETPLACE / SHEET DI SIDEBAR
st.sidebar.title("🛒 Pilih Platform / Marketplace")
selected_marketplace = st.sidebar.radio(
    "Pilih Target Marketplace:", ["Shopee", "Tokopedia"]
)

# Simpan state marketplace aktif agar saat pindah menu tidak reset
if (
    "active_marketplace" not in st.session_state
    or st.session_state["active_marketplace"] != selected_marketplace
):
  st.session_state["active_marketplace"] = selected_marketplace
  st.session_state["content_db"] = load_database(selected_marketplace)
  if "edit_index" in st.session_state:
    del st.session_state["edit_index"]

# Inisialisasi Session State jika belum ada
if "content_db" not in st.session_state:
  st.session_state["content_db"] = load_database(selected_marketplace)

st.sidebar.markdown(f"📌 **Tab Aktif GSheet:** `{selected_marketplace}`")

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
    st.subheader(
        f"📋 Tabel Manajemen Campaign & Banner ({selected_marketplace})"
    )
  with col_btn:
    if st.button("🔄 Refresh Data", key="ref_menu1"):
      st.session_state["content_db"] = load_database(selected_marketplace)
      st.success("Data berhasil diperbarui dari Google Sheets!")
      st.rerun()

  df = st.session_state["content_db"]

  if df.empty:
    st.info(
        f"Belum ada data campaign untuk {selected_marketplace}. Silakan"
        " tambah melalui menu **Tambah Campaign Baru**."
    )
  else:
    col_f1, col_f2 = st.columns(2)
    with col_f1:
      filter_status = st.selectbox(
          "Filter Status", ["Semua", "Draft", "Pending", "Done"]
      )
    with col_f2:
      search_query = st.text_input(
          "🔍 Cari Campaign Name / SKU", placeholder="Ketik kata kunci..."
      )

    filtered_df = df.copy()
    if filter_status != "Semua":
      filtered_df = filtered_df[
          filtered_df["STATUS"].str.lower() == filter_status.lower()
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
        uk_str = (
            ", ".join(row["UKURAN BANNER"])
            if isinstance(row["UKURAN BANNER"], list)
            else str(row["UKURAN BANNER"])
        )

        with st.container(border=True):
          c1, c2, c3, c4, c5, c6, c7 = st.columns(
              [1.4, 1.1, 1, 1, 1, 1, 0.7]
          )

          with c1:
            st.markdown(f"📌 **No. {row['NO']}**")
            c_name_short = (
                str(row["CAMPAIGN NAME"])[:40] + "..."
                if len(str(row["CAMPAIGN NAME"])) > 40
                else str(row["CAMPAIGN NAME"])
            )
            with st.popover("📄 Detail Campaign"):
              st.text_area(
                  "Campaign Name",
                  value=str(row["CAMPAIGN NAME"]),
                  height=130,
                  disabled=True,
                  label_visibility="collapsed",
              )
            st.write(f"🏷️ {c_name_short}")

          with c2:
            st.markdown("📐 **Ukuran:**")
            st.write(uk_str if uk_str else "-")

          with c3:
            st.markdown("📦 **Product Show:**")
            prod_val = str(row["PRODUCT SHOOW BANNER"])
            if "http" in prod_val:
              st.markdown(f"[Buka Link Produk]({prod_val})")
            else:
              sku_short = (
                  prod_val[:25] + "..." if len(prod_val) > 25 else prod_val
              )
              with st.popover("📦 Lihat SKU"):
                st.text_area(
                    "Product Show",
                    value=prod_val,
                    height=100,
                    disabled=True,
                    label_visibility="collapsed",
                )
              st.write(sku_short if sku_short else "-")

          with c4:
            st.markdown("🖼️ **Referensi:**")
            img_path = str(row["CONTOH/REFERENSI BANNER"])
            if img_path and os.path.exists(img_path):
              st.image(img_path, width=80)
            elif img_path:
              st.write(img_path)
            else:
              st.write("-")

          with c5:
            st.markdown("🔗 **Link Drive:**")
            drive_val = str(row["LINK DRIVE"])
            if drive_val.startswith("http"):
              st.markdown(f"[Buka Link]({drive_val})")
            else:
              st.write(drive_val if drive_val else "-")

          with c6:
            st.markdown("📊 **Status:**")
            st.write(f"**{row['STATUS']}**")
            catatan_txt = (
                str(row["CATATAN"])
                if pd.notna(row["CATATAN"]) and row["CATATAN"] != ""
                else "-"
            )
            if catatan_txt != "-":
              with st.popover("📝 Catatan"):
                st.write(catatan_txt)

          with c7:
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
                save_database(
                    st.session_state["content_db"], selected_marketplace
                )
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
                  value=str(r_data["PRODUCT SHOOW BANNER"]),
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
              db_df.loc[e_idx, "CAMPAIGN NAME"] = edit_camp_name
              db_df.loc[e_idx, "UKURAN BANNER"] = edit_ukuran
              db_df.loc[e_idx, "PRODUCT SHOOW BANNER"] = edit_product
              db_df.loc[e_idx, "LINK DRIVE"] = edit_link_drive
              db_df.loc[e_idx, "STATUS"] = edit_status
              db_df.loc[e_idx, "CONTOH/REFERENSI BANNER"] = edit_referensi
              db_df.loc[e_idx, "CATATAN"] = edit_catatan

              save_database(db_df, selected_marketplace)
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
  st.subheader(
      f"➕ Tambah Baris Campaign Baru ke Google Sheets ({selected_marketplace})"
  )

  with st.form("form_tambah_campaign", clear_on_submit=True):
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
      status = st.selectbox(
          "Status", ["Draft", "Pending", "Done"], index=0
      )  # Default Draft

    uploaded_file = st.file_uploader(
        "Upload Contoh / Referensi Banner (Gambar)",
        type=["png", "jpg", "jpeg"],
    )
    catatan = st.text_area("Catatan Tambahan")

    submit_button = st.form_submit_button("Simpan ke Google Sheets")

    if submit_button:
      if camp_name:
        st.session_state["content_db"] = load_database(selected_marketplace)
        current_len = len(st.session_state["content_db"])
        new_no = current_len + 1

        ref_path = ""
        if uploaded_file is not None:
          ref_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
          with open(ref_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        new_data = {
            "NO": new_no,
            "CAMPAIGN NAME": camp_name,
            "UKURAN BANNER": ukuran_banner,
            "PRODUCT SHOOW BANNER": product_show,
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
        save_database(st.session_state["content_db"], selected_marketplace)
        st.success(
            f"Berhasil! Campaign baru tersimpan ke sheet '{selected_marketplace}'"
            " di Google Sheets."
        )
      else:
        st.warning("Mohon setidaknya isi kolom **Campaign Name**.")

# ==========================================
# MENU 3: APPROVAL / STATUS CHECKER
# ==========================================
elif menu == "👔 Approval / Status Checker":
  st.subheader(
      f"👔 Ringkasan Status Campaign ({selected_marketplace}) & WhatsApp"
      " Reminder"
  )

  df = st.session_state["content_db"]

  if df.empty:
    st.info("Belum ada data.")
  else:
    total_data = len(df)
    total_done = len(df[df["STATUS"].str.lower() == "done"])
    total_pending = len(df[df["STATUS"].str.lower() == "pending"])
    total_draft = len(df[df["STATUS"].str.lower() == "draft"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Campaign", total_data)
    c2.metric("Status Done", total_done)
    c3.metric("Status Pending", total_pending)
    c4.metric("Status Draft", total_draft)

    st.markdown("---")
    st.markdown(
        f"### 📲 Kirim Pengingat WhatsApp Tim ({selected_marketplace})"
    )

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

    uk_str_wa = (
        ", ".join(selected_row["UKURAN BANNER"])
        if isinstance(selected_row["UKURAN BANNER"], list)
        else str(selected_row["UKURAN BANNER"])
    )
    pesan_wa = (
        f"Halo *{pilihan_admin}*, mohon bantuannya untuk cek campaign *{selected_marketplace}* berikut:\n\n"
        f"📌 *Campaign:* {selected_row['CAMPAIGN NAME']}\n"
        f"📐 *Ukuran:* {uk_str_wa}\n"
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
        " Buka WhatsApp & Kirim Pesan</button></a>",
        unsafe_allow_html=True,
    )
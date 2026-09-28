import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Control de Liquidaciones 2026-2027", layout="wide")

# AQUÍ PEGAS EL LINK DE TU GOOGLE SHEET (Reemplaza el texto entre comillas)
SHEET_URL = "AQUÍ_PEGA_TU_LINK_DE_GOOGLE_SHEETS"

# Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🍇 Control y Conciliación de Liquidaciones 2026-2027")
st.subheader("Agrícola Curutarán & Agroclas")

# Catálogo oficial de ranchos
catalogo_df = pd.DataFrame([
    {"Agricola": "Agrícola Curutarán", "Rancho": "Ramizal 17040", "Productor": "244470", "Cultivo": "Zarzamora"},
    {"Agricola": "Agrícola Curutarán", "Rancho": "Potrero Org 16860", "Productor": "244470", "Cultivo": "Zarzamora Orgánica"},
    {"Agricola": "Agroclas", "Rancho": "Nacimiento 10313", "Productor": "28470", "Cultivo": "Zarzamora Conv."},
    {"Agricola": "Agroclas", "Rancho": "Claro Org 21752", "Productor": "28470", "Cultivo": "Zarzamora Orgánica"},
])

# Cargar datos desde Google Sheets
@st.cache_data(ttl=5)
def cargar_datos(worksheet_name):
    try:
        data = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=5)
        return data if not data.empty else pd.DataFrame(columns=["Fecha", "Agricola", "Rancho", "Monto USD", "Notas"])
    except Exception:
        return pd.DataFrame(columns=["Fecha", "Agricola", "Rancho", "Monto USD", "Notas"])

depositos_df = cargar_datos("Depositos")
liquidaciones_df = cargar_datos("Liquidaciones")

# Menú de navegación
menu = st.sidebar.radio("Navegación / Menú", [
    "📊 Dashboard / Conciliación", 
    "💵 Registrar Depósito", 
    "📄 Registrar Liquidación", 
    "🏡 Catálogo de Ranchos"
])

if menu == "📊 Dashboard / Conciliación":
    st.header("📊 Resumen de Conciliación General")
    
    df_dep = depositos_df.groupby("Rancho")["Monto USD"].sum().reset_index().rename(columns={"Monto USD": "Total Depósitos"}) if not depositos_df.empty and "Monto USD" in depositos_df.columns else pd.DataFrame(columns=["Rancho", "Total Depósitos"])
    df_liq = liquidaciones_df.groupby("Rancho")["Monto USD"].sum().reset_index().rename(columns={"Monto USD": "Total Liquidado"}) if not liquidaciones_df.empty and "Monto USD" in liquidaciones_df.columns else pd.DataFrame(columns=["Rancho", "Total Liquidado"])
    
    resumen = pd.merge(catalogo_df, df_dep, on="Rancho", how="left").fillna(0)
    resumen = pd.merge(resumen, df_liq, on="Rancho", how="left").fillna(0)
    
    resumen["Diferencia"] = resumen["Total Depósitos"] - resumen["Total Liquidado"]
    resumen["Estatus"] = resumen["Diferencia"].apply(lambda x: "✅ CONCILIADO" if round(x, 2) == 0 else ("⚠️ PENDIENTE LIQ" if x > 0 else "🔴 SOBREPAGO"))
    
    st.dataframe(resumen.style.format({"Total Depósitos": "${:,.2f}", "Total Liquidado": "${:,.2f}", "Diferencia": "${:,.2f}"}), use_container_width=True)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Depósitos Banco", f"${resumen['Total Depósitos'].sum():,.2f}")
    col2.metric("Total Reportado Liquidaciones", f"${resumen['Total Liquidado'].sum():,.2f}")
    col3.metric("Diferencia Por Conciliar", f"${resumen['Diferencia'].sum():,.2f}")

elif menu == "💵 Registrar Depósito":
    st.header("💵 Captura de Depósito Bancario")
    with st.form("form_deposito", clear_on_submit=True):
        fecha = st.date_input("Fecha del Pago", datetime.date.today())
        rancho_sel = st.selectbox("Rancho", catalogo_df["Rancho"].tolist())
        agricola_sel = catalogo_df[catalogo_df["Rancho"] == rancho_sel]["Agricola"].values[0]
        monto = st.number_input("Monto Depósito (USD)", min_value=0.0, step=100.0, format="%.2f")
        notas = st.text_input("Concepto / Notas")
        
        submitted = st.form_submit_button("Guardar Depósito")
        if submitted:
            nueva_fila = pd.DataFrame([{"Fecha": str(fecha), "Agricola": agricola_sel, "Rancho": rancho_sel, "Monto USD": monto, "Notas": notas}])
            updated_df = pd.concat([depositos_df, nueva_fila], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="Depositos", data=updated_df)
            st.success("✅ Depósito registrado e insertado en Google Sheets")
            st.cache_data.clear()
            st.rerun()

    st.subheader("Historial de Depósitos Capturados")
    st.dataframe(depositos_df, use_container_width=True)

elif menu == "📄 Registrar Liquidación":
    st.header("📄 Captura de Reporte de Liquidación Driscoll's")
    with st.form("form_liq", clear_on_submit=True):
        fecha = st.date_input("Fecha de Liquidación", datetime.date.today())
        rancho_sel = st.selectbox("Rancho", catalogo_df["Rancho"].tolist())
        agricola_sel = catalogo_df[catalogo_df["Rancho"] == rancho_sel]["Agricola"].values[0]
        monto = st.number_input("Monto Liquidación (USD)", min_value=0.0, step=100.0, format="%.2f")
        notas = st.text_input("No. Liquidación / Notas")
        
        submitted = st.form_submit_button("Guardar Liquidación")
        if submitted:
            nueva_fila = pd.DataFrame([{"Fecha": str(fecha), "Agricola": agricola_sel, "Rancho": rancho_sel, "Monto USD": monto, "Notas": notas}])
            updated_df = pd.concat([liquidaciones_df, nueva_fila], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="Liquidaciones", data=updated_df)
            st.success("✅ Liquidación registrada e insertada en Google Sheets")
            st.cache_data.clear()
            st.rerun()

    st.subheader("Historial de Liquidaciones Capturadas")
    st.dataframe(liquidaciones_df, use_container_width=True)

elif menu == "🏡 Catálogo de Ranchos":
    st.header("🏡 Catálogo Oficial de Ranchos")
    st.table(catalogo_df)

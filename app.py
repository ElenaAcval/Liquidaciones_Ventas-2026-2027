import streamlit as st
import pandas as pd
import datetime
import requests

st.set_page_config(page_title="Control de Liquidaciones 2026-2027", layout="wide")

WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwFVBKZXITSe9PFBe0HuQzxW6Yar4e7c29s9P8QIrzYKtlQu1zWPQnLOiFyRvkhZZr7/exec"
SHEET_ID = "19zhFm7ety4JL6sImcWF5HLHGBo_X1jkRD37FQtgndP4"

st.title("🍇 Control y Conciliación de Liquidaciones 2026-2027")

catalogo_df = pd.DataFrame([
    {"Agricola": "Agrícola Curutarán", "Rancho": "Ramizal 17040", "Productor": "244470", "Cultivo": "Zarzamora"},
    {"Agricola": "Agrícola Curutarán", "Rancho": "Potrero Org 16860", "Productor": "244470", "Cultivo": "Zarzamora Orgánica"},
    {"Agricola": "Agroclas", "Rancho": "Nacimiento 10313", "Productor": "28470", "Cultivo": "Zarzamora Conv."},
    {"Agricola": "Agroclas", "Rancho": "Claro Org 21752", "Productor": "28470", "Cultivo": "Zarzamora Orgánica"},
])

@st.cache_data(ttl=2)
def cargar_hoja(nombre_hoja):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={nombre_hoja}"
    try:
        df = pd.read_csv(url)
        df["Monto USD"] = pd.to_numeric(df["Monto USD"], errors="coerce").fillna(0)
        return df
    except Exception:
        return pd.DataFrame(columns=["Fecha", "Agricola", "Rancho", "Monto USD", "Notas", "Diferencia (USD)", "Estatus"])

dep_curutaran = cargar_hoja("Depositos_Curutaran")
liq_curutaran = cargar_hoja("Liquidaciones_Curutaran")
dep_agroclas = cargar_hoja("Depositos_Agroclas")
liq_agroclas = cargar_hoja("Liquidaciones_Agroclas")

depositos_all = pd.concat([dep_curutaran, dep_agroclas], ignore_index=True)
liquidaciones_all = pd.concat([liq_curutaran, liq_agroclas], ignore_index=True)

def calcular_conciliacion_rancho(rancho, nuevo_monto, tipo):
    dep_rancho = depositos_all[depositos_all["Rancho"] == rancho]["Monto USD"].sum()
    liq_rancho = liquidaciones_all[liquidaciones_all["Rancho"] == rancho]["Monto USD"].sum()
    
    if tipo == "Depositos":
        dep_rancho += nuevo_monto
    elif tipo == "Liquidaciones":
        liq_rancho += nuevo_monto
        
    diferencia = dep_rancho - liq_rancho
    if round(diferencia, 2) == 0:
        estatus = "✅ CONCILIADO"
    elif diferencia > 0:
        estatus = "⚠️ PENDIENTE LIQ"
    else:
        estatus = "🔴 SOBREPAGO"
        
    return diferencia, estatus

menu = st.sidebar.radio("Navegación", [
    "📊 Dashboard y Conciliación", 
    "💵 Registrar Depósito", 
    "📄 Registrar Liquidación", 
    "🏡 Catálogo de Ranchos"
])

if menu == "📊 Dashboard y Conciliación":
    st.header("📊 Resumen de Conciliación General")
    agricola_filtro = st.selectbox("Seleccionar Agrícola", ["Todas", "Agrícola Curutarán", "Agroclas"])
    
    if agricola_filtro != "Todas":
        cat_filtrado = catalogo_df[catalogo_df["Agricola"] == agricola_filtro]
        dep_f = depositos_all[depositos_all["Agricola"] == agricola_filtro]
        liq_f = liquidaciones_all[liquidaciones_all["Agricola"] == agricola_filtro]
    else:
        cat_filtrado = catalogo_df
        dep_f = depositos_all
        liq_f = liquidaciones_all

    df_dep = dep_f.groupby("Rancho")["Monto USD"].sum().reset_index().rename(columns={"Monto USD": "Total Depósitos"}) if not dep_f.empty else pd.DataFrame(columns=["Rancho", "Total Depósitos"])
    df_liq = liq_f.groupby("Rancho")["Monto USD"].sum().reset_index().rename(columns={"Monto USD": "Total Liquidado"}) if not liq_f.empty else pd.DataFrame(columns=["Rancho", "Total Liquidado"])
    
    resumen = pd.merge(cat_filtrado, df_dep, on="Rancho", how="left").fillna(0)
    resumen = pd.merge(resumen, df_liq, on="Rancho", how="left").fillna(0)
    
    resumen["Diferencia (USD)"] = resumen["Total Depósitos"] - resumen["Total Liquidado"]
    resumen["Estatus"] = resumen["Diferencia (USD)"].apply(
        lambda x: "✅ CONCILIADO" if round(x, 2) == 0 else ("⚠️ PENDIENTE LIQ" if x > 0 else "🔴 SOBREPAGO")
    )
    
    st.dataframe(
        resumen.style.format({
            "Total Depósitos": "${:,.2f}", 
            "Total Liquidado": "${:,.2f}", 
            "Diferencia (USD)": "${:,.2f}"
        }), 
        use_container_width=True
    )

elif menu == "💵 Registrar Depósito":
    st.header("💵 Registrar Depósito Bancario")
    with st.form("form_deposito", clear_on_submit=True):
        fecha = st.date_input("Fecha del Pago", datetime.date.today())
        rancho_sel = st.selectbox("Rancho", catalogo_df["Rancho"].tolist())
        agricola_sel = catalogo_df[catalogo_df["Rancho"] == rancho_sel]["Agricola"].values[0]
        monto = st.number_input("Monto Depósito (USD)", min_value=0.0, step=100.0, format="%.2f")
        notas = st.text_input("Concepto / Notas")
        
        submitted = st.form_submit_button("Guardar Depósito")
        if submitted:
            dif, estatus = calcular_conciliacion_rancho(rancho_sel, monto, "Depositos")
            payload = {
                "tipo": "Depositos",
                "fecha": str(fecha),
                "agricola": agricola_sel,
                "rancho": rancho_sel,
                "monto": monto,
                "notas": notas,
                "diferencia": dif,
                "estatus": estatus
            }
            res = requests.post(WEBHOOK_URL, json=payload)
            if res.status_code == 200:
                st.success(f"✅ Depósito guardado con diferencia (${dif:,.2f}) en {agricola_sel}")
                st.cache_data.clear()
                st.rerun()

    st.subheader("Historial de Depósitos Capturados")
    st.dataframe(depositos_all, use_container_width=True)

elif menu == "📄 Registrar Liquidación":
    st.header("📄 Registrar Liquidación Driscoll's")
    with st.form("form_liq", clear_on_submit=True):
        fecha = st.date_input("Fecha de Liquidación", datetime.date.today())
        rancho_sel = st.selectbox("Rancho", catalogo_df["Rancho"].tolist())
        agricola_sel = catalogo_df[catalogo_df["Rancho"] == rancho_sel]["Agricola"].values[0]
        monto = st.number_input("Monto Liquidación (USD)", min_value=0.0, step=100.0, format="%.2f")
        notas = st.text_input("No. Liquidación / Notas")
        
        submitted = st.form_submit_button("Guardar Liquidación")
        if submitted:
            dif, estatus = calcular_conciliacion_rancho(rancho_sel, monto, "Liquidaciones")
            payload = {
                "tipo": "Liquidaciones",
                "fecha": str(fecha),
                "agricola": agricola_sel,
                "rancho": rancho_sel,
                "monto": monto,
                "notas": notas,
                "diferencia": dif,
                "estatus": estatus
            }
            res = requests.post(WEBHOOK_URL, json=payload)
            if res.status_code == 200:
                st.success(f"✅ Liquidación guardada con diferencia (${dif:,.2f}) en {agricola_sel}")
                st.cache_data.clear()
                st.rerun()

    st.subheader("Historial de Liquidaciones Capturadas")
    st.dataframe(liquidaciones_all, use_container_width=True)

elif menu == "🏡 Catálogo de Ranchos":
    st.header("🏡 Catálogo Oficial de Ranchos")
    st.table(catalogo_df)

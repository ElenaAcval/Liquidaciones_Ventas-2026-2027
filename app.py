import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="Control de Liquidaciones y Depósitos", layout="wide")

st.title("🍇 Control y Conciliación de Liquidaciones 2026-2027")
st.subheader("Agrícola Curutarán & Agroclas")

# Estado inicial del catálogo de ranchos (Fijo)
if "catalogo" not in st.session_state:
    st.session_state.catalogo = pd.DataFrame([
        {"Agricola": "Agrícola Curutarán", "Rancho": "Ramizal 17040", "Productor": "244470", "Cultivo": "Zarzamora"},
        {"Agricola": "Agrícola Curutarán", "Rancho": "Potrero Org 16860", "Productor": "244470", "Cultivo": "Zarzamora Orgánica"},
        {"Agricola": "Agroclas", "Rancho": "Nacimiento 10313", "Productor": "28470", "Cultivo": "Zarzamora Conv."},
        {"Agricola": "Agroclas", "Rancho": "Claro Org 21752", "Productor": "28470", "Cultivo": "Zarzamora Orgánica"},
    ])

# Tablas de captura de datos (Inician VACÍAS para la nueva temporada)
if "depositos" not in st.session_state:
    st.session_state.depositos = pd.DataFrame(columns=["Fecha", "Agricola", "Rancho", "Monto USD", "Notas"])

if "liquidaciones" not in st.session_state:
    st.session_state.liquidaciones = pd.DataFrame(columns=["Fecha", "Agricola", "Rancho", "Monto USD", "Notas"])

# Menú Lateral
menu = st.sidebar.radio("Navegación / Menú", [
    "📊 Dashboard / Conciliación", 
    "💵 Registrar Depósito", 
    "📄 Registrar Liquidación", 
    "🏡 Catálogo de Ranchos",
    "⚙️ Opciones de Limpieza"
])

if menu == "📊 Dashboard / Conciliación":
    st.header("📊 Resumen de Conciliación General")
    
    # Calcular Totales por Rancho
    if not st.session_state.depositos.empty:
        df_dep = st.session_state.depositos.groupby("Rancho")["Monto USD"].sum().reset_index().rename(columns={"Monto USD": "Total Depósitos"})
    else:
        df_dep = pd.DataFrame(columns=["Rancho", "Total Depósitos"])
        
    if not st.session_state.liquidaciones.empty:
        df_liq = st.session_state.liquidaciones.groupby("Rancho")["Monto USD"].sum().reset_index().rename(columns={"Monto USD": "Total Liquidado"})
    else:
        df_liq = pd.DataFrame(columns=["Rancho", "Total Liquidado"])
    
    resumen = pd.merge(st.session_state.catalogo, df_dep, on="Rancho", how="left").fillna(0)
    resumen = pd.merge(resumen, df_liq, on="Rancho", how="left").fillna(0)
    
    resumen["Diferencia"] = resumen["Total Depósitos"] - resumen["Total Liquidado"]
    resumen["Estatus"] = resumen["Diferencia"].apply(lambda x: "✅ CONCILIADO" if round(x, 2) == 0 else ("⚠️ PENDIENTE LIQ" if x > 0 else "🔴 SOBREPAGO"))
    
    st.dataframe(resumen.style.format({"Total Depósitos": "${:,.2f}", "Total Liquidado": "${:,.2f}", "Diferencia": "${:,.2f}"}), use_container_width=True)
    
    # Métricas Globales
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Depósitos Banco", f"${resumen['Total Depósitos'].sum():,.2f}")
    col2.metric("Total Reportado Liquidaciones", f"${resumen['Total Liquidado'].sum():,.2f}")
    col3.metric("Diferencia Por Conciliar", f"${resumen['Diferencia'].sum():,.2f}")

elif menu == "💵 Registrar Depósito":
    st.header("💵 Captura de Depósito Bancario")
    with st.form("form_deposito", clear_on_submit=True):
        fecha = st.date_input("Fecha del Pago", datetime.date.today())
        rancho_sel = st.selectbox("Rancho", st.session_state.catalogo["Rancho"].tolist())
        agricola_sel = st.session_state.catalogo[st.session_state.catalogo["Rancho"] == rancho_sel]["Agricola"].values[0]
        monto = st.number_input("Monto Depósito (USD)", min_value=0.0, step=100.0, format="%.2f")
        notas = st.text_input("Concepto / Notas")
        
        submitted = st.form_submit_button("Guardar Depósito")
        if submitted:
            nueva_fila = pd.DataFrame([{"Fecha": fecha, "Agricola": agricola_sel, "Rancho": rancho_sel, "Monto USD": monto, "Notas": notas}])
            st.session_state.depositos = pd.concat([st.session_state.depositos, nueva_fila], ignore_index=True)
            st.success("✅ ¡Depósito registrado con éxito!")
            st.rerun()

    st.subheader("Historial de Depósitos Capturados")
    st.dataframe(st.session_state.depositos, use_container_width=True)

elif menu == "📄 Registrar Liquidación":
    st.header("📄 Captura de Reporte de Liquidación Driscoll's")
    with st.form("form_liq", clear_on_submit=True):
        fecha = st.date_input("Fecha de Liquidación", datetime.date.today())
        rancho_sel = st.selectbox("Rancho", st.session_state.catalogo["Rancho"].tolist())
        agricola_sel = st.session_state.catalogo[st.session_state.catalogo["Rancho"] == rancho_sel]["Agricola"].values[0]
        monto = st.number_input("Monto Liquidación (USD)", min_value=0.0, step=100.0, format="%.2f")
        notas = st.text_input("No. Liquidación / Notas")
        
        submitted = st.form_submit_button("Guardar Liquidación")
        if submitted:
            nueva_fila = pd.DataFrame([{"Fecha": fecha, "Agricola": agricola_sel, "Rancho": rancho_sel, "Monto USD": monto, "Notas": notas}])
            st.session_state.liquidaciones = pd.concat([st.session_state.liquidaciones, nueva_fila], ignore_index=True)
            st.success("✅ ¡Liquidación registrada con éxito!")
            st.rerun()

    st.subheader("Historial de Liquidaciones Capturadas")
    st.dataframe(st.session_state.liquidaciones, use_container_width=True)

elif menu == "🏡 Catálogo de Ranchos":
    st.header("🏡 Catálogo Oficial de Ranchos y Cultivos (Temporada 2026-2027)")
    st.table(st.session_state.catalogo)

elif menu == "⚙️ Opciones de Limpieza":
    st.header("⚙️ Reiniciar Tablas / Limpiar Datos")
    st.warning("⚠️ Precaución: Esta acción borrará los registros de la pantalla actual.")
    
    if st.button("🔴 Borrar todos los depósitos y liquidaciones (Empezar de 0)"):
        st.session_state.depositos = pd.DataFrame(columns=["Fecha", "Agricola", "Rancho", "Monto USD", "Notas"])
        st.session_state.liquidaciones = pd.DataFrame(columns=["Fecha", "Agricola", "Rancho", "Monto USD", "Notas"])
        st.success("✅ Se han borrado todos los datos. Las capturas están en $0.00.")
        st.rerun()
import streamlit as st
import pandas as pd
from PIL import Image
import io
import json
import google.generativeai as genai

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="LTDS Scanner Real", page_icon="👁️")

# ==========================================
# 0. CONFIGURACIÓN API (NECESARIA)
# ==========================================
# Busca tu API Key aquí: https://aistudio.google.com/app/apikey
# Puedes ponerla directo en el código (no recomendado para compartir) 
# o mejor en un input de la barra lateral.

with st.sidebar:
    st.header("🔑 Configuración")
    api_key = st.text_input("Ingresa tu Google API Key", type="password")
    st.info("Consigue tu clave gratis en Google AI Studio.")

if api_key:
    genai.configure(api_key=api_key)

# ==========================================
# 1. OPTIMIZACIÓN DE IMAGEN
# ==========================================
def optimizar_imagen(archivo_imagen, ancho_maximo=800):
    """Reduce la imagen para enviarla rápido a la API"""
    try:
        imagen = Image.open(archivo_imagen)
        if imagen.mode != "RGB":
            imagen = imagen.convert("RGB")

        if imagen.width > ancho_maximo:
            ratio = ancho_maximo / float(imagen.width)
            nuevo_alto = int((float(imagen.height) * float(ratio)))
            imagen = imagen.resize((ancho_maximo, nuevo_alto), Image.Resampling.LANCZOS)
        
        return imagen
    except Exception as e:
        st.error(f"Error imagen: {e}")
        return None

# ==========================================
# 2. INTELIGENCIA ARTIFICIAL (GEMINI 1.5 FLASH)
# ==========================================
def detectar_con_ia(imagen_pil):
    if not api_key:
        st.error("❌ Falta la API Key.")
        return []

    try:
        # Usamos el modelo Flash que es rápido y barato
        model = genai.GenerativeModel('gemini-2.5-flash')

        # El Prompt es la "instrucción" para la IA
        prompt = """
        Analiza esta imagen de cartas Magic: The Gathering.
        Identifica cada carta visible.
        Devuelve SOLO un array JSON (sin markdown ```json) con estos campos para cada carta:
        - "nombre": Nombre exacto en inglés.
        - "set_codigo": Código de 3 letras de la edición (si lo ves, si no pon "???").
        - "idioma": "EN", "ES", "JP" según corresponda.
        - "condicion": Estima "NM" (perfecta) o "LP" (algo gastada).
        Si no hay cartas, devuelve un array vacío [].
        """

        # Llamada real a la IA
        response = model.generate_content([prompt, imagen_pil])
        
        # Limpieza de la respuesta (a veces la IA pone comillas de código)
        texto_limpio = response.text.replace("```json", "").replace("```", "").strip()
        
        return json.loads(texto_limpio)

    except Exception as e:
        st.error(f"Error en la IA: {e}")
        return []

# ==========================================
# 3. INTERFAZ VISUAL
# ==========================================
st.title("👁️ LTDS Scanner (IA Real)")
st.markdown("Sube fotos y la IA de Google extraerá los nombres y ediciones.")

uploaded_files = st.file_uploader("Fotos de cartas", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)

if uploaded_files and st.button("🚀 Iniciar Escaneo con IA"):
    if not api_key:
        st.warning("⚠️ Primero pon tu API Key en la barra lateral.")
        st.stop()

    resultados_totales = []
    barra = st.progress(0)
    
    for i, file in enumerate(uploaded_files):
        # 1. Optimizar (PIL)
        img_optimizada = optimizar_imagen(file)
        
        if img_optimizada:
            # 2. Detectar (Llamada a Google)
            with st.spinner(f"Analizando {file.name}..."):
                cartas = detectar_con_ia(img_optimizada)
            
            # 3. Guardar
            if cartas:
                for c in cartas:
                    c['archivo_origen'] = file.name
                    resultados_totales.append(c)
        
        barra.progress((i + 1) / len(uploaded_files))

    # Resultados
    if resultados_totales:
        st.success(f"¡Detectadas {len(resultados_totales)} cartas!")
        df = pd.DataFrame(resultados_totales)
        
        # Editor para corregir errores de la IA
        df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        
        # Descarga
        csv = df_editado.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Descargar CSV", data=csv, file_name="ltds_scan_ia.csv", mime="text/csv")
    else:
        st.warning("No se detectaron cartas. Intenta con mejor iluminación.")

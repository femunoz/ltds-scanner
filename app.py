import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
import time
import os

# --- Autenticación Simple ---
password = st.sidebar.text_input("🔑 Contraseña de Acceso", type="password")

#pass=""
#if "PASS" in st.secrets:
#    pass = st.secrets["PASS"]

if password != "ltds2005": # Cambia esto por una contraseña que solo tú sepas
    st.warning("⛔ Esta herramienta es de uso interno. Ingresa la contraseña para continuar.")
    st.stop() # Detiene la ejecución del resto del código aquí

# --- Si la contraseña es correcta, el código sigue abajo ---

# --- Configuración de API Key (Lógica Híbrida) ---
# 1. Primero intenta buscar en los Secretos de la Nube
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
    st.sidebar.success("✅ API Key cargada desde secretos") # Mensaje para confirmar que funcionó

# 2. Si no, la pide manual (para cuando pruebas en local sin secretos)
else:
    api_key = st.sidebar.text_input("Pega tu Google API Key aquí:", type="password")

# --- Validación ---
if not api_key:
    st.warning("⚠️ Necesitas una API Key para continuar.")
    st.stop() # Detiene la app aquí si no hay clave

genai.configure(api_key=api_key)


#############


# --- Configuración de la Página ---
st.set_page_config(
    page_title="Escáner LTDS - Multi",
    page_icon="🧙‍♂️",
    layout="wide"
)

# --- Sidebar para Configuración ---
with st.sidebar:
    #st.header("⚙️ Configuración")
    #api_key = st.text_input("Pega tu Google API Key aquí:", type="password")
    #st.info("Obtén tu clave gratis en aistudio.google.com")
    
    st.divider()
    st.write("### Instrucciones:")
    st.write("1. Selecciona VARIAS fotos a la vez.")
    st.write("2. Presiona 'Procesar Lote'.")
    st.write("3. Espera a que la barra de progreso termine.")
    st.write("4. Corrige y descarga.")

# --- Lógica Principal ---
st.title("🧙‍♂️ La Tiendita de Schroedinger - Escáner Masivo")
st.markdown("Sube **múltiples fotos** de tus carpetas (hojas de 3x3) y procésalas en lote.")

# Selector de archivo (Múltiple)
uploaded_files = st.file_uploader(
    "Elige las imágenes...", 
    type=["jpg", "jpeg", "png"], 
    accept_multiple_files=True  # <--- ESTO PERMITE VARIOS ARCHIVOS
)

# Inicializar estado
if 'df_result' not in st.session_state:
    st.session_state.df_result = None

def procesar_imagen(image, key):
    """Envía la imagen a Gemini y retorna un JSON."""
    genai.configure(api_key=key)
    
    # Usamos el modelo que te funcionó (gemini-pro-vision o gemini-1.5-flash-latest)
    # models/gemini-2.5-flashgemini-2.5-flash
    # Si 'gemini-pro-vision' te dio problemas de 404 antes, usa el que te funcionó en el test
    model = genai.GenerativeModel('gemini-2.5-flash') 
    
    prompt = """
    Actúa como un experto en Magic: The Gathering. Analiza esta imagen.
    Identifica todas las cartas visibles (usualmente 9 en una grilla).
    Devuelve una respuesta EXCLUSIVAMENTE en formato JSON válido (sin bloques de código markdown, solo el raw json).
    El JSON debe ser una lista de objetos con estas claves exactas:
    - "card_name_en": Nombre oficial en inglés.
    - "set_code": El código de 3 letras de la edición (abajo a la izquierda).
    - "language": El idioma de la carta (Spanish, English, Japanese, etc).
    
    Si la imagen está borrosa o no hay cartas, devuelve una lista vacía [].
    """
    
    try:
        response = model.generate_content([prompt, image])
        text_response = response.text
        
        # Limpieza forzada del string json
        text_response = text_response.replace("```json", "").replace("```", "").strip()
        
        data = json.loads(text_response)
        return data
    except Exception as e:
        # Si falla una foto, no queremos que se caiga todo el proceso
        print(f"Error en una imagen: {e}")
        return []

# --- Interfaz de Usuario ---

if uploaded_files:
    num_files = len(uploaded_files)
    st.info(f"Has cargado {num_files} imágenes. Listo para procesar.")
    
    # Botón de acción
    if st.button(f"✨ Procesar Lote ({num_files} imágenes)", type="primary"):
        if not api_key:
            st.warning("⚠️ Por favor ingresa tu API Key en la barra lateral.")
        else:
            all_cards = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Loop para procesar cada imagen una por una
            for i, uploaded_file in enumerate(uploaded_files):
                # Actualizar barra de progreso
                status_text.text(f"Analizando imagen {i+1} de {num_files}...")
                
                # Cargar imagen
                image = Image.open(uploaded_file)
                
                # Llamada a la IA
                cartas_encontradas = procesar_imagen(image, api_key)
                
                # Acumular resultados
                if cartas_encontradas:
                    all_cards.extend(cartas_encontradas)
                
                # Actualizar barra
                progress_bar.progress((i + 1) / num_files)
                
                # Pequeña pausa para no saturar la API (Rate Limit) si subes muchas
                time.sleep(1) 
            
            status_text.text("¡Procesamiento completado!")
            progress_bar.empty()
            
            if all_cards:
                st.session_state.df_result = pd.DataFrame(all_cards)
                st.success(f"¡Se detectaron un total de {len(all_cards)} cartas en las {num_files} fotos!")
            else:
                st.warning("No se pudieron detectar cartas. Revisa la iluminación de las fotos.")

# --- Sección de Resultados y Edición ---
if st.session_state.df_result is not None:
    st.divider()
    st.subheader("📝 Inventario Consolidado")
    
    # Métricas rápidas
    col1, col2 = st.columns(2)
    col1.metric("Total Cartas", len(st.session_state.df_result))
    col2.metric("Ediciones Distintas", st.session_state.df_result['set_code'].nunique() if 'set_code' in st.session_state.df_result.columns else 0)

    # Data Editor
    edited_df = st.data_editor(
        st.session_state.df_result,
        num_rows="dynamic",
        use_container_width=True
    )
    
    # Botón de descarga
    csv = edited_df.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="💾 Descargar CSV Maestro",
        data=csv,
        file_name="inventario_ltds_masivo.csv",
        mime="text/csv",
    )

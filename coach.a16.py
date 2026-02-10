import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import requests
import matplotlib
matplotlib.use('Agg') # Esto evita errores en servidores sin pantalla
import matplotlib.pyplot as plt
import google.generativeai as genai
from datetime import datetime, date
import matplotlib.pyplot as plt
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# ==========================================================
# 1. CONFIGURACIÓN (TUS DATOS)
# ==========================================================
CLIENT_ID = "198338"
CLIENT_SECRET = "e9936dead1f99e10abe7811005c2c259500eab20"
REFRESH_TOKEN = "6b035548510091a4457ced5895daf9a77cd3d9dc"
FTP = 183
GEMINI_API_KEY = "AIzaSyAzjTgcNSV0r8Gu6R_xghIpcxomkwkl1r0"  # Google Gemini
TELEGRAM_TOKEN = "8219550242:AAFB66oY-5Bl-WOKqCsS-Nt8O0tCF85DRDY"
week_number = date.today().isocalendar()[1]


# ==========================================================
# 2. ENTRENAMIENTOS (TUS 8 BLOQUES)
# ==========================================================
def thursday_workout(FTP, week):
    block = (week - 1) % 8 + 1
    rutinas = {
        1: {"name": "Sweet Spot 4x8", "details": f"20' Z2\n4×8' a {int(FTP*0.90)}-{int(FTP*0.95)}W\n4' rec"},
        2: {"name": "Sweet Spot 3x12", "details": f"20' Z2\n3×12' a {int(FTP*0.88)}-{int(FTP*0.94)}W\n5' rec"},
        3: {"name": "Umbral 3x10", "details": f"20' Z2\n3×10' a {int(FTP*0.95)}-{int(FTP*1.00)}W\n5' rec"},
        4: {"name": "Descarga Tempo", "details": f"15' Z2\n2×15' a {int(FTP*0.80)}-{int(FTP*0.85)}W\n5' rec"},
        5: {"name": "VO2 5x4", "details": f"20' Z2\n5×4' a {int(FTP*1.05)}-{int(FTP*1.10)}W\n4' rec"},
        6: {"name": "Sweet Spot Mixto", "details": "20' Z2\n2×10' + 1×20' Sweet Spot"},
        7: {"name": "Umbral Largo 2x20", "details": f"20' Z2\n2×20' a {int(FTP*0.92)}-{int(FTP*0.97)}W\n5' rec"},
        8: {"name": "Descarga Z2", "details": "Rodaje suave regenerativo"}
    }
    return rutinas.get(block, rutinas[8])

# ==========================================================
# 3. STRAVA Y GRÁFICA
# ==========================================================
system_context = "Eres un coach experto."
weekly_tss = 0

def actualizar_datos_strava():
    global system_context, weekly_tss
    print("🔗 Conectando con Strava...")
    try:
        auth = requests.post("https://www.strava.com/oauth/token", 
                             data={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, 
                                   "refresh_token": REFRESH_TOKEN, "grant_type": "refresh_token"}).json()
        headers = {"Authorization": f"Bearer {auth['access_token']}"}
        activities = requests.get("https://www.strava.com/api/v3/athlete/activities", 
                                   headers=headers, params={"per_page": 10}).json()
        
        fechas, tss_lista, detalles = [], [], []
        total = 0
        for act in activities:
            if act.get("type") == "Ride" and act.get("average_watts"):
                tss = int((act["elapsed_time"]/3600) * ((act["average_watts"]/FTP)**2) * 100)
                total += tss
                fecha = act["start_date"][:10]
                fechas.append(fecha); tss_lista.append(tss)
                detalles.append(f"- {fecha}: {tss} TSS")
        
        weekly_tss = total
        system_context = f"Coach experto. FTP:{FTP}. TSS Semanal:{total}. Datos:\n" + "\n".join(detalles)
        
        plt.style.use('dark_background')
        plt.figure(figsize=(10,5))
        plt.bar(fechas[::-1], tss_lista[::-1], color='gold')
        plt.title(f"TSS: {total}")
        plt.savefig('grafica.png')
        plt.close()
    except Exception as e:
        print(f"Error Strava: {e}")

# ==========================================================
# 4. BOT TELEGRAM
# ==========================================================
async def entreno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wk = thursday_workout(FTP, week_number)
    await update.message.reply_text(f"📋 *PLAN:* {wk['name']}\n{wk['details']}", parse_mode='Markdown')

async def progreso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    actualizar_datos_strava()
    try:
        await update.message.reply_photo(photo=open('grafica.png', 'rb'), caption=f"TSS: {weekly_tss}")
    except:
        await update.message.reply_text("Gráfica no lista.")

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Buscamos el modelo que Google te deje usar hoy
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        nombre_modelo = next((m for m in modelos if "1.5" in m), modelos[0])
        
        model = genai.GenerativeModel(nombre_modelo)
        res = model.generate_content(f"{system_context}\n\nPregunta: {update.message.text}")
        await update.message.reply_text(res.text)
    except Exception as e:
        print(f"Error IA: {e}")
        await update.message.reply_text("La IA está tardando en responder o hay mucha carga. Prueba en un momento.")

# ==========================================================
# 5. LANZAMIENTO
# ==========================================================
if __name__ == '__main__':
    genai.configure(api_key=GEMINI_API_KEY)
    actualizar_datos_strava()
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('entreno', entreno))
    app.add_handler(CommandHandler('progreso', progreso))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), responder))
    
    print("🚀 BOT ONLINE")
    app.run_polling(drop_pending_updates=True)
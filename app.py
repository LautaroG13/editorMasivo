from flask import Flask, render_template, jsonify, request, redirect
import requests
import time
import math
import os

app = Flask(__name__)

# =========================================================================
# ⚙️ CONFIGURACIÓN DINÁMICA DE TIENDANUBE (Variables libres y globales)
# =========================================================================
# Al dejarlas globales a nivel de servidor, evitamos que al recargar la página
# o hacer F5 desde el iframe los valores se vuelvan "None".
STORE_ID = None
ACCESS_TOKEN = None
USER_AGENT = 'web@cotillonchialvo.com'

# Credenciales oficiales fijas de tu aplicación en Tiendanube Partners
CLIENT_ID = "34257"
CLIENT_SECRET = "b042eab988f05ab5b94a29ac96565ca993d679571b3078a5"

def obtener_headers():
    """Genera los headers dinámicos utilizando el token activo en memoria"""
    global ACCESS_TOKEN, USER_AGENT
    return {
        'Authentication': f'bearer {ACCESS_TOKEN}',
        'User-Agent': USER_AGENT,
        'Content-Type': 'application/json'
    }
# =========================================================================


# =========================================================================
# 🧭 RUTAS DE CONEXIÓN Y FLUJO OAUTH (PASO PREVIO)
# =========================================================================

@app.route('/')
def index():
    """
    Ruta raíz: Evalúa si la tienda ya otorgó los permisos.
    Si no hay token, exige el paso previo de conexión. Si hay, abre la grilla.
    """
    global STORE_ID, ACCESS_TOKEN
    print(f"🔍 Evaluando credenciales en Raíz -> ID: {STORE_ID}, Token: {ACCESS_TOKEN}")
    
    if not ACCESS_TOKEN or not STORE_ID:
        return render_template('conectar.html', tienda_id="No conectada", token="No generado", mostrar_boton=False)
    
    return render_template('dashboard.html')


@app.route('/auth/callback')
def auth_callback():
    """
    Callback Oficial: Recibe el código temporal de Tiendanube, solicita el
    Access Token definitivo y lo guarda inmediatamente en la memoria del servidor.
    """
    global STORE_ID, ACCESS_TOKEN
    code = request.args.get('code')
    
    if not code:
        print("❌ Error: Código de autorización ausente en los parámetros de la URL.")
        return "Error: No se recibió el código de autorización", 400

    token_url = "https://www.tiendanube.com/apps/authorize/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code
    }
    
    try:
        print("📡 Enviando solicitud de Token a Tiendanube...")
        response = requests.post(token_url, json=payload).json()
        
        # Guardado inmediato en variables globales del backend
        ACCESS_TOKEN = response.get('access_token')
        STORE_ID = response.get('user_id') 
        
        print(f"✅ Credenciales fijadas en memoria -> Tienda ID: {STORE_ID}")
        print(f"✅ Token generado exitosamente: {ACCESS_TOKEN[:10]}...")
        
        # Renderiza la plantilla intermedia pasándole los datos reales capturados
        return render_template('conectar.html', tienda_id=STORE_ID, token=ACCESS_TOKEN, mostrar_boton=True)

    except Exception as e:
        print(f"❌ Error crítico durante el proceso de Callback OAuth: {str(e)}")
        return f"Error en la vinculación OAuth: {str(e)}", 500


@app.route('/api/confirmar_conexion', methods=['POST'])
def confirmar_conexion():
    """
    Valida y confirma que los tokens sigan vigentes en el backend antes
    de liberar el acceso completo al Dashboard.
    """
    global STORE_ID, ACCESS_TOKEN
    
    if STORE_ID and ACCESS_TOKEN:
        print("==================================================")
        print("====== ✅ EDITOR MASIVO INTEGRADO Y ACTIVADO ======")
        print(f"   Tienda en producción: {STORE_ID}")
        print("==================================================")
        return jsonify({"status": "success"})
    else:
        print("⚠️ Alerta: Se intentó confirmar la conexión pero las variables estaban vacías.")
        return jsonify({"status": "error", "message": "Faltan credenciales en el servidor."}), 400


# =========================================================================
# 📦 LÓGICA DE PRODUCTOS (Imagen primero + Atributos Dinámicos Reales)
# =========================================================================

@app.route('/api/productos', methods=['GET'])
def obtener_productos():
    """
    Carga Infinita: Trae bloques de a 50 productos desde Tiendanube,
    desglosa sus variantes y mapea las propiedades reales de la tienda.
    """
    global STORE_ID
    page = request.args.get('page', default=1, type=int)
    per_page = 50
    print(f"🔄 Carga Infinita: Descargando bloque de productos número {page}...")
    
    url_fetch = f"https://api.tiendanube.com/v1/{STORE_ID}/products?page={page}&per_page={per_page}"
    productos_grilla = []
    
    try:
        headers_dinamicos = obtener_headers()
        res = requests.get(url_fetch, headers=headers_dinamicos)
        
        if res.status_code != 200 or not res.json():
            print(f"⚠️ Fin de catálogo o respuesta inválida en página {page}. Status: {res.status_code}")
            return jsonify({"last_page": page, "data": []})
            
        total_productos = int(res.headers.get('X-Total-Count', 11500))
        max_paginas = math.ceil(total_productos / per_page)
        datos = res.json()
        
        for prod in datos:
            nombre_prod = prod.get('name', {}).get('es', 'Sin nombre')
            
            # --- CAPTURA DE NOMBRES DE PROPIEDADES REALES ---
            # En vez de "Propiedad 1", extrae "Color", "Talle", etc., según configuró el cliente.
            atributos_prod = prod.get('attributes', [])
            nombres_propiedades = []
            for attr in atributos_prod:
                if isinstance(attr, dict) and attr.get('es'):
                    nombres_propiedades.append(attr['es'])
                elif isinstance(attr, str):
                    nombres_propiedades.append(attr)
            
            # Procesamiento de categorías vinculadas
            categories_list = []
            if prod.get('categories'):
                for c in prod.get('categories', []):
                    if c.get('name') and c['name'].get('es'):
                        categories_list.append(c['name']['es'])
            categorias_str = ", ".join(categories_list) if categories_list else ""
            
            url_id = prod.get('handle', {}).get('es', '')
            mostrar_str = "Si" if prod.get('published') else "No"
            seo_title = prod.get('seo_title', {}).get('es', '')
            seo_description = prod.get('seo_description', {}).get('es', '')
            brand = prod.get('brand', '')
            
            tags_str = ", ".join(prod['tags']) if prod.get('tags') and isinstance(prod['tags'], list) else ''
            images = prod.get('images', [])
            url_imagen = images[0].get('src', '') if images else ''
            free_shipping = "Si" if prod.get('free_shipping') else "No"

            # Iteramos las variantes del producto para armar las filas individuales de la grilla
            for v in prod.get('variants', []):
                values_prop = [val['es'] for val in v.get('values', []) if val.get('es')]
                
                productos_grilla.append({
                    # 1. ATRIBUTO PRINCIPAL EXIGIDO: La URL de la imagen en primer lugar
                    "url_imagen": str(url_imagen),
                    
                    # Identificadores de control interno
                    "id_prod": str(prod.get('id', '')),
                    "id_var": str(v.get('id', '')),
                    "url_id": str(url_id),
                    "nombre": str(nombre_prod),
                    "categorias": str(categorias_str),
                    "sku": str(v.get('sku', '')) if v.get('sku') is not None else '',
                    "barcode": str(v.get('barcode', '')) if v.get('barcode') is not None else '',
                    "marca": str(brand),
                    
                    # Valores comerciales numéricos
                    "precio": float(v.get('price', 0)) if v.get('price') else 0.0,
                    "precio_promo": float(v.get('promotional_price', 0)) if v.get('promotional_price') else 0.0,
                    "costo": float(v.get('cost', 0)) if v.get('cost') else 0.0,
                    "stock": int(v.get('stock', 0)) if v.get('stock') is not None else 0,
                    
                    # Datos logísticos de envío
                    "peso": float(v.get('weight', 0)) if v.get('weight') else 0.0,
                    "alto": float(v.get('height', 0)) if v.get('height') else 0.0,
                    "ancho": float(v.get('width', 0)) if v.get('width') else 0.0,
                    "profundidad": float(v.get('depth', 0)) if v.get('depth') else 0.0,
                    
                    # Visibilidad, SEO y etiquetas
                    "mostrar": str(mostrar_str),
                    "envio_gratis": str(free_shipping),
                    "tags": str(tags_str),
                    "seo_titulo": str(seo_title),
                    "seo_desc": str(seo_description),
                    
                    # Mapeo de Atributos Dinámicos Reales (Evitando textos estáticos)
                    "prop_nombre_1": nombres_propiedades[0] if len(nombres_propiedades) >= 1 else "",
                    "prop_valor_1": values_prop[0] if len(values_prop) >= 1 else "",
                    
                    "prop_nombre_2": nombres_propiedades[1] if len(nombres_propiedades) >= 2 else "",
                    "prop_valor_2": values_prop[1] if len(values_prop) >= 2 else "",
                    
                    "prop_nombre_3": nombres_propiedades[2] if len(nombres_propiedades) >= 3 else "",
                    "prop_valor_3": values_prop[2] if len(values_prop) >= 3 else ""
                })
                
        print(f"📊 Bloque {page} procesado con éxito. Cantidad de filas devueltas: {len(productos_grilla)}")
        return jsonify({"last_page": max_paginas, "data": productos_grilla})

    except Exception as e:
        print(f"❌ Error crítico en ruta /api/productos al procesar página {page}: {str(e)}")
        return jsonify({"last_page": page, "data": []})


# =========================================================================
# 💾 LÓGICA DE SINCRONIZACIÓN Y GUARDADO MASIVO
# =========================================================================

@app.route('/api/guardar', methods=['POST'])
def guardar_cambios():
    """
    Recibe el array de modificaciones enviadas por la grilla editable,
    formatea los campos numéricos y ejecuta los PUT hacia la API de Tiendanube.
    """
    global STORE_ID
    cambios = request.json
    print(f"\n🚀 Sincronizando {len(cambios)} modificaciones habilitadas con Tienda Nube...")
    
    def limpiar_flotante(valor, predeterminado=0.0):
        if valor is None or str(valor).strip() == "": 
            return predeterminado
        try: 
            return float(str(valor).replace(",", ".").strip())
        except Exception as err:
            print(f"   ⚠️ Fallo al convertir flotante '{valor}', aplicando default: {err}")
            return predeterminado

    def limpiar_entero(valor, predeterminado=0):
        if valor is None or str(valor).strip() == "": 
            return predeterminado
        try: 
            return int(str(valor).strip())
        except Exception as err:
            print(f"   ⚠️ Fallo al convertir entero '{valor}', aplicando default: {err}")
            return predeterminado

    contador_ok = 0
    headers_dinamicos = obtener_headers()
    
    for item in cambios:
        pid = item.get('id_prod')
        vid = item.get('id_var')
        
        # 1. Actualizar datos del Producto Base (Padre)
        payload_producto = {}
        if 'nombre' in item and item['nombre']:
            payload_producto['name'] = {'es': item['nombre'].strip()}
        if 'marca' in item and item['marca']:
            payload_producto['brand'] = item['marca'].strip()
        if 'mostrar' in item:
            payload_producto['published'] = True if item['mostrar'] == "Si" else False
        if 'envio_gratis' in item:
            payload_producto['free_shipping'] = True if item['envio_gratis'] == "Si" else False

        if payload_producto:
            url_prod = f"https://api.tiendanube.com/v1/{STORE_ID}/products/{pid}"
            try: 
                res_prod = requests.put(url_prod, headers=headers_dinamicos, json=payload_producto)
                if res_prod.status_code not in [200, 201]:
                    print(f"   ⚠️ Error actualizando base {pid}. Código: {res_prod.status_code}")
            except Exception as e:
                print(f"   ❌ Error de conexión en Producto Padre {pid}: {e}")

        # 2. Actualizar datos específicos de la Variante (Hijo)
        payload_variante = {
            "stock": limpiar_entero(item.get('stock'), predeterminado=0),
            "sku": None if str(item.get('sku', '')).strip() == '' else item.get('sku'),
            "barcode": None if str(item.get('barcode', '')).strip() == '' else item.get('barcode'),
            "weight": limpiar_flotante(item.get('peso')),
            "height": limpiar_flotante(item.get('alto'), predeterminado=5.0),
            "width": limpiar_flotante(item.get('ancho'), predeterminado=5.0),
            "depth": limpiar_flotante(item.get('profundidad'), predeterminado=5.0)
        }
        
        if item.get('precio') and str(item['precio']).strip() != "":
            payload_variante["price"] = round(limpiar_flotante(item['precio']))
        if item.get('precio_promo') and str(item['precio_promo']).strip() != "":
            payload_variante["promotional_price"] = round(limpiar_flotante(item['precio_promo']))
        if item.get('costo') and str(item['costo']).strip() != "":
            payload_variante["cost"] = round(limpiar_flotante(item['costo']))

        url_variant = f"https://api.tiendanube.com/v1/{STORE_ID}/products/{pid}/variants/{vid}"
        
        try:
            res = requests.put(url_variant, headers=headers_dinamicos, json=payload_variante)
            
            # Control de Rate Limiting (Límite de llamadas API de Tiendanube)
            if res.status_code == 429:
                print("⏳ API Límite alcanzado (429). Esperando 6 segundos de penalización...")
                time.sleep(6)
                res = requests.put(url_variant, headers=headers_dinamicos, json=payload_variante)
                
            if res.status_code in [200, 201]: 
                contador_ok += 1
            else:
                print(f"   ⚠️ Fallo en Variante {vid}. HTTP {res.status_code}: {res.text[:120]}")
        except Exception as e: 
            print(f"   ❌ Error de red al intentar actualizar variante {vid}: {e}")
            
        # Pequeño delay de cortesía para estabilizar el hilo de peticiones
        time.sleep(0.04)

    print(f"💾 Guardado Masivo Finalizado. Sincronizaciones exitosas: {contador_ok}/{len(cambios)}")
    return jsonify({"status": "success", "actualizados": contador_ok})


# =========================================================================
# 🔓 SEGURIDAD E INCRUSTACIÓN (Liberar Iframe del panel de administración)
# =========================================================================

@app.after_request
def permitir_iframe(response):
    """
    Intercepta las respuestas salientes de Flask para remover las restricciones 
    tradicionales de renderizado en frames, permitiendo que corra dentro del panel Tiendanube.
    """
    response.headers.pop('X-Frame-Options', None)
    response.headers['Content-Security-Policy'] = "frame-ancestors 'self' https://*.tiendanube.com https://*.mitiendanube.com https://admin.tiendanube.com;"
    return response


if __name__ == '__main__':
    # Render asigna el puerto mediante variables de entorno en producción
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
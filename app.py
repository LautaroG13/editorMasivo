from flask import Flask, render_template, jsonify, request
import requests
import time
import math

app = Flask(__name__)

# =========================================================================
# ⚙️ CONFIGURACIÓN Y CREDENCIALES OFICIALES DE TIENDA NUBE
# =========================================================================
STORE_ID = '6951198'
ACCESS_TOKEN = '9aa7e54a1e006c78d6f3aad2c670f47587e1e816'
USER_AGENT = 'web@cotillonchialvo.com'

HEADERS = {
    'Authentication': f'bearer {ACCESS_TOKEN}',
    'User-Agent': USER_AGENT,
    'Content-Type': 'application/json'
}
# =========================================================================

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/productos', methods=['GET'])
def obtener_productos():
    page = request.args.get('page', default=1, type=int)
    per_page = 50
    print(f"🔄 Carga Infinita: Descargando bloque {page}...")
    
    url_fetch = f"https://api.tiendanube.com/v1/{STORE_ID}/products?page={page}&per_page={per_page}"
    productos_grilla = []
    
    try:
        res = requests.get(url_fetch, headers=HEADERS)
        if res.status_code != 200 or not res.json():
            return jsonify({"last_page": page, "data": []})
            
        total_productos = int(res.headers.get('X-Total-Count', 11500))
        max_paginas = math.ceil(total_productos / per_page)
        datos = res.json()
        
        for prod in datos:
            nombre_prod = prod.get('name', {}).get('es', 'Sin nombre')
            
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

            for v in prod.get('variants', []):
                values_prop = [val['es'] for val in v.get('values', []) if val.get('es')]
                
                productos_grilla.append({
                    "id_prod": str(prod.get('id', '')),
                    "id_var": str(v.get('id', '')),
                    "url_imagen": str(url_imagen),
                    "url_id": str(url_id),
                    "nombre": str(nombre_prod),
                    "categorias": str(categorias_str),
                    "sku": str(v.get('sku', '')) if v.get('sku') is not None else '',
                    "barcode": str(v.get('barcode', '')) if v.get('barcode') is not None else '',
                    "marca": str(brand),
                    "precio": float(v.get('price', 0)) if v.get('price') else 0.0,
                    "precio_promo": float(v.get('promotional_price', 0)) if v.get('promotional_price') else 0.0,
                    "costo": float(v.get('cost', 0)) if v.get('cost') else 0.0,
                    "stock": int(v.get('stock', 0)) if v.get('stock') is not None else 0,
                    "peso": float(v.get('weight', 0)) if v.get('weight') else 0.0,
                    "alto": float(v.get('height', 0)) if v.get('height') else 0.0,
                    "ancho": float(v.get('width', 0)) if v.get('width') else 0.0,
                    "profundidad": float(v.get('depth', 0)) if v.get('depth') else 0.0,
                    "mostrar": str(mostrar_str),
                    "envio_gratis": str(free_shipping),
                    "tags": str(tags_str),
                    "seo_titulo": str(seo_title),
                    "seo_desc": str(seo_description),
                    "prop_nombre_1": "Propiedad 1" if len(values_prop) >= 1 else "",
                    "prop_valor_1": values_prop[0] if len(values_prop) >= 1 else "",
                    "prop_nombre_2": "Propiedad 2" if len(values_prop) >= 2 else "",
                    "prop_valor_2": values_prop[1] if len(values_prop) >= 2 else "",
                    "prop_nombre_3": "Propiedad 3" if len(values_prop) >= 3 else "",
                    "prop_valor_3": values_prop[2] if len(values_prop) >= 3 else ""
                })
                
        return jsonify({"last_page": max_paginas, "data": productos_grilla})
    except Exception as e:
        print(f"❌ Error en carga: {e}")
        return jsonify({"last_page": page, "data": []})

@app.route('/api/guardar', methods=['POST'])
def guardar_cambios():
    cambios = request.json
    print(f"\n🚀 Sincronizando {len(cambios)} modificaciones habilitadas con Tienda Nube...")
    
    # Convierte textos con coma o vacíos en números decimales limpios para Python
    def limpiar_flotante(valor, predeterminado=0.0):
        if valor is None or str(valor).strip() == "":
            return predeterminado
        try:
            return float(str(valor).replace(",", ".").strip())
        except:
            return predeterminado

    # Convierte celdas vacías de stock en un 0 entero para evitar el error ValueError
    def limpiar_entero(valor, predeterminado=0):
        if valor is None or str(valor).strip() == "":
            return predeterminado
        try:
            return int(str(valor).strip())
        except:
            return predeterminado

    contador_ok = 0
    for item in cambios:
        pid = item.get('id_prod')
        vid = item.get('id_var')
        
        # 1. Actualizar campos globales del Producto Padre (si se modificaron)
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
                requests.put(url_prod, headers=HEADERS, json=payload_producto)
            except Exception as e:
                print(f"   ⚠️ Error actualizando base {pid}: {e}")

        # 2. Actualizar Variante: Stock, Logística (Medidas) y Precios
        payload_variante = {
            "stock": limpiar_entero(item.get('stock'), predeterminado=0),
            "sku": None if str(item.get('sku', '')).strip() == '' else item.get('sku'),
            "barcode": None if str(item.get('barcode', '')).strip() == '' else item.get('barcode'),
            "weight": limpiar_flotante(item.get('peso')),
            "height": limpiar_flotante(item.get('alto'), predeterminado=5.0),
            "width": limpiar_flotante(item.get('ancho'), predeterminado=5.0),
            "depth": limpiar_flotante(item.get('profundidad'), predeterminado=5.0)
        }
        
        # Validación individual para precios para que no falle si se borran
        if item.get('precio') and str(item['precio']).strip() != "":
            payload_variante["price"] = round(limpiar_flotante(item['precio']))
        if item.get('precio_promo') and str(item['precio_promo']).strip() != "":
            payload_variante["promotional_price"] = round(limpiar_flotante(item['precio_promo']))
        if item.get('costo') and str(item['costo']).strip() != "":
            payload_variante["cost"] = round(limpiar_flotante(item['costo']))

        url_variant = f"https://api.tiendanube.com/v1/{STORE_ID}/products/{pid}/variants/{vid}"
        
        try:
            res = requests.put(url_variant, headers=HEADERS, json=payload_variante)
            if res.status_code == 429:
                print("⏳ Límite alcanzado, esperando 6 segundos...")
                time.sleep(6)
                res = requests.put(url_variant, headers=HEADERS, json=payload_variante)
                
            if res.status_code in [200, 201]:
                contador_ok += 1
                print(f"   ✅ Variante {vid} actualizada exitosamente.")
            else:
                print(f"   ⚠️ Error en Variante {vid}: {res.text[:150]}")
        except Exception as e:
            print(f"   ❌ Error de red: {e}")
            
        time.sleep(0.04)

    return jsonify({"status": "success", "actualizados": contador_ok})

if __name__ == '__main__':
    import os
    # Render nos da el puerto en una variable de entorno. Si no existe, usa el 5000 por defecto.
    port = int(os.environ.get('PORT', 5000))
    # CRUCIAL: '0.0.0.0' le dice a Flask que escuche conexiones externas, no solo locales.
    app.run(host='0.0.0.0', port=port)

    import os
import requests
from flask import Flask, request, redirect, render_template

app = Flask(__name__)

# NOTA: En un entorno real y seguro, estas credenciales se guardan como Variables de Entorno en Render.
# Por ahora para testear, podés copiarlas de la pestaña "Resumen" de Tiendanube.
CLIENT_ID = "34257" 
CLIENT_SECRET = "b042eab988f05ab5b94a29ac96565ca993d679571b3078a5" # <-- Copiá el código largo tapado con puntitos de tu pantalla de Tiendanube

@app.route('/')
def home():
    # Aquí cargás tu dashboard actual (dashboard.html)
    return render_template('dashboard.html')

# ESTA ES LA NUEVA RUTA CLAVE PARA TIENDANUBE
@app.route('/auth/callback')
def auth_callback():
    # 1. Tiendanube te envía un código temporal por la URL
    code = request.args.get('code')
    
    if not code:
        return "Error: No se recibió el código de autorización de Tiendanube.", 400

    # 2. Intercambiamos ese código por el Access Token definitivo de la tienda
    token_url = "https://www.tiendanube.com/apps/authorize/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code
    }
    
    try:
        response = requests.post(token_url, json=payload).json()
        access_token = response.get('access_token')
        user_id = response.get('user_id') # Este es el ID único de la tienda que te instaló
        
        # Con este access_token ya tenés permiso de editar sus productos.
        print(f"¡Éxito! Tienda conectada: ID {user_id} - Token: {access_token}")
        
        # 3. Redirigimos al usuario a la página principal de tu editor
        return redirect('/')
        
    except Exception as e:
        return f"Error en la autenticación: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

    try:
        response = requests.post(token_url, json=payload).json()
        access_token = response.get('access_token')
        user_id = response.get('user_id') 
        
        # Guardamos el token para usarlo después
        tienda_actual["access_token"] = access_token
        tienda_actual["user_id"] = user_id
        
        print(f"¡Éxito! Tienda conectada: ID {user_id}")
        
        # IMPORTANTE: Redirigir de vuelta al administrador de Tiendanube
        # Esto le avisa a Tiendanube que la instalación fue un éxito rotundo
        return redirect(f"https://admin.tiendanube.com/admin/apps/{user_id}/installed")

    except Exception as e:
        return f"Error: {str(e)}", 500
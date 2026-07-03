from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
CORS(app)

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/mmq'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui_cambiarla_en_produccion'

# Configuración para subida de archivos
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'mov', 'avi', 'webm'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# Crear carpetas de uploads si no existen
os.makedirs(os.path.join(UPLOAD_FOLDER, 'events'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'gallery'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'hero'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'sponsors'), exist_ok=True)

db = SQLAlchemy(app)

# ==================== HELPER FUNCTIONS ====================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== MODELOS ====================

class EventSetting(db.Model):
    __tablename__ = 'event_settings'
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(255), nullable=False)
    event_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    date = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(500))
    category = db.Column(db.String(50), default='evento')
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': str(self.id),
            'title': self.title,
            'date': self.date,
            'description': self.description,
            'image': self.image,
            'category': self.category,
            'featured': self.featured,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class GalleryItem(db.Model):
    __tablename__ = 'gallery_items'
    id = db.Column(db.Integer, primary_key=True)
    src = db.Column(db.String(500), nullable=False)
    alt = db.Column(db.String(255), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(50), default='image')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    event = db.relationship('Event', backref='gallery_items')

    def to_dict(self):
        return {
            'id': str(self.id),
            'src': self.src,
            'alt': self.alt,
            'event': self.event.title if self.event else '',
            'event_id': self.event_id,
            'year': self.year,
            'type': self.type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class HeroSettings(db.Model):
    __tablename__ = 'hero_settings'
    id = db.Column(db.Integer, primary_key=True)
    hero_video = db.Column(db.String(500))
    event_date = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'heroVideo': self.hero_video,
            'eventDate': self.event_date,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Sponsor(db.Model):
    __tablename__ = 'sponsors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    logo = db.Column(db.String(500), nullable=False)
    tier = db.Column(db.String(50), nullable=False)  # principal, oro, plata, colaborador
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'logo': self.logo,
            'tier': self.tier,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class AdminUser(db.Model):
    __tablename__ = 'admin_users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ==================== RUTAS DE ARCHIVOS ====================

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Servir archivos subidos"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/upload/<category>', methods=['POST'])
def upload_file(category):
    """Subir archivo (category: events, gallery, hero, sponsors)"""
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No se envió ningún archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'Nombre de archivo vacío'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], category, filename)
            file.save(filepath)
            
            file_url = f"/uploads/{category}/{filename}"
            return jsonify({
                'status': 'success',
                'message': 'Archivo subido exitosamente',
                'url': file_url
            }), 201
        
        return jsonify({'status': 'error', 'message': 'Tipo de archivo no permitido'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== RUTAS DE EVENTOS ====================

@app.route('/api/events', methods=['GET'])
def get_events():
    """Obtener todos los eventos"""
    try:
        events = Event.query.order_by(Event.created_at.desc()).all()
        return jsonify({
            'status': 'success',
            'events': [event.to_dict() for event in events]
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/events', methods=['POST'])
def create_event():
    """Crear un nuevo evento con archivo"""
    try:
        title = request.form.get('title')
        date = request.form.get('date')
        description = request.form.get('description')
        category = request.form.get('category', 'evento')
        featured = request.form.get('featured', 'false') == 'true'
        
        image_url = ''
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'events', filename)
                file.save(filepath)
                image_url = f"/uploads/events/{filename}"
        
        new_event = Event(
            title=title,
            date=date,
            description=description,
            image=image_url,
            category=category,
            featured=featured
        )
        
        db.session.add(new_event)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Evento creado exitosamente',
            'event': new_event.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/events/<int:event_id>', methods=['PUT'])
def update_event(event_id):
    """Actualizar un evento existente"""
    try:
        event = Event.query.get_or_404(event_id)
        
        event.title = request.form.get('title', event.title)
        event.date = request.form.get('date', event.date)
        event.description = request.form.get('description', event.description)
        event.category = request.form.get('category', event.category)
        event.featured = request.form.get('featured', 'false') == 'true'
        
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'events', filename)
                file.save(filepath)
                event.image = f"/uploads/events/{filename}"
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Evento actualizado exitosamente',
            'event': event.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/events/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    """Eliminar un evento"""
    try:
        event = Event.query.get_or_404(event_id)
        db.session.delete(event)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Evento eliminado exitosamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== RUTAS DE GALERÍA ====================

@app.route('/api/gallery', methods=['GET'])
def get_gallery():
    """Obtener todos los elementos de la galería"""
    try:
        items = GalleryItem.query.order_by(GalleryItem.created_at.desc()).all()
        return jsonify({
            'status': 'success',
            'items': [item.to_dict() for item in items]
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/gallery', methods=['POST'])
def add_gallery_item():
    """Añadir un elemento a la galería con archivo"""
    try:
        alt = request.form.get('alt')
        event_id = request.form.get('event_id')
        year = request.form.get('year')
        item_type = request.form.get('type', 'image')
        
        if not event_id:
            return jsonify({'status': 'error', 'message': 'Debe seleccionar un evento'}), 400
        
        file_url = ''
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'gallery', filename)
                file.save(filepath)
                file_url = f"/uploads/gallery/{filename}"
        
        if not file_url:
            return jsonify({'status': 'error', 'message': 'Debe subir un archivo'}), 400
        
        new_item = GalleryItem(
            src=file_url,
            alt=alt,
            event_id=int(event_id),
            year=int(year),
            type=item_type
        )
        
        db.session.add(new_item)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Elemento añadido a la galería',
            'item': new_item.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/gallery/<int:item_id>', methods=['DELETE'])
def delete_gallery_item(item_id):
    """Eliminar un elemento de la galería"""
    try:
        item = GalleryItem.query.get_or_404(item_id)
        db.session.delete(item)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Elemento eliminado de la galería'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/gallery/bulk', methods=['POST'])
def add_gallery_items_bulk():
    """Añadir múltiples elementos a la galería con archivos"""
    try:
        event_id = request.form.get('event_id')
        year = request.form.get('year')
        item_type = request.form.get('type', 'image')
        
        if not event_id:
            return jsonify({'status': 'error', 'message': 'Debe seleccionar un evento'}), 400
        
        # Obtener todos los archivos
        files = request.files.getlist('files[]')
        
        if not files or len(files) == 0:
            return jsonify({'status': 'error', 'message': 'Debe subir al menos un archivo'}), 400
        
        successful_items = []
        failed_items = []
        
        for file in files:
            try:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    filename = f"{timestamp}_{filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'gallery', filename)
                    file.save(filepath)
                    file_url = f"/uploads/gallery/{filename}"
                    
                    # Generar descripción automática basada en el nombre del archivo
                    alt = secure_filename(file.filename).rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')
                    
                    new_item = GalleryItem(
                        src=file_url,
                        alt=alt,
                        event_id=int(event_id),
                        year=int(year),
                        type=item_type
                    )
                    
                    db.session.add(new_item)
                    successful_items.append({
                        'filename': file.filename,
                        'alt': alt
                    })
                else:
                    failed_items.append({
                        'filename': file.filename,
                        'error': 'Tipo de archivo no permitido'
                    })
            except Exception as e:
                failed_items.append({
                    'filename': file.filename,
                    'error': str(e)
                })
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'{len(successful_items)} archivos subidos exitosamente',
            'successful': successful_items,
            'failed': failed_items,
            'total': len(files),
            'success_count': len(successful_items),
            'failed_count': len(failed_items)
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== RUTAS DE HERO ====================

@app.route('/api/hero-settings', methods=['GET'])
def get_hero_settings():
    """Obtener configuración del hero"""
    try:
        settings = HeroSettings.query.first()
        if not settings:
            settings = HeroSettings(
                hero_video='',
                event_date='2025-08-10T06:00:00'
            )
            db.session.add(settings)
            db.session.commit()
        
        return jsonify({
            'status': 'success',
            'settings': settings.to_dict()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/hero-settings/video', methods=['PUT'])
def update_hero_video():
    """Actualizar video del hero con archivo"""
    try:
        settings = HeroSettings.query.first()
        if not settings:
            settings = HeroSettings()
            db.session.add(settings)
        
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'hero', filename)
                file.save(filepath)
                settings.hero_video = f"/uploads/hero/{filename}"
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Video del hero actualizado',
            'settings': settings.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/hero-settings/event-date', methods=['PUT'])
def update_event_date():
    """Actualizar fecha del evento"""
    try:
        data = request.get_json()
        settings = HeroSettings.query.first()
        
        if not settings:
            settings = HeroSettings(event_date=data['eventDate'])
            db.session.add(settings)
        else:
            settings.event_date = data['eventDate']
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Fecha del evento actualizada',
            'settings': settings.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== RUTAS DE PATROCINADORES ====================

@app.route('/api/sponsors', methods=['GET'])
def get_sponsors():
    """Obtener todos los patrocinadores"""
    try:
        sponsors = Sponsor.query.all()
        return jsonify({
            'status': 'success',
            'sponsors': [sponsor.to_dict() for sponsor in sponsors]
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/sponsors', methods=['POST'])
def create_sponsor():
    """Crear un nuevo patrocinador con archivo"""
    try:
        name = request.form.get('name')
        tier = request.form.get('tier')
        
        logo_url = ''
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'sponsors', filename)
                file.save(filepath)
                logo_url = f"/uploads/sponsors/{filename}"
        
        if not logo_url:
            return jsonify({'status': 'error', 'message': 'Debe subir un logo'}), 400
        
        new_sponsor = Sponsor(
            name=name,
            logo=logo_url,
            tier=tier
        )
        
        db.session.add(new_sponsor)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Patrocinador creado exitosamente',
            'sponsor': new_sponsor.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/sponsors/<int:sponsor_id>', methods=['DELETE'])
def delete_sponsor(sponsor_id):
    """Eliminar un patrocinador"""
    try:
        sponsor = Sponsor.query.get_or_404(sponsor_id)
        db.session.delete(sponsor)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Patrocinador eliminado exitosamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== RUTA DE INFORMACIÓN DEL EVENTO ====================

@app.route('/api/event-info', methods=['GET'])
def get_event_info():
    """Obtener información del evento principal"""
    try:
        event = EventSetting.query.filter_by(is_active=True).first()
        
        if event:
            return jsonify({
                'status': 'success',
                'eventName': event.event_name,
                'eventDate': event.event_date.isoformat(),
            })
        
        return jsonify({
            'status': 'error',
            'message': 'No hay eventos activos'
        }), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== RUTAS DE AUTENTICACIÓN ====================

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Login de administrador"""
    try:
        data = request.get_json()
        password = data.get('password')
        
        if password == 'mmq2025admin':
            return jsonify({
                'status': 'success',
                'message': 'Login exitoso',
                'isAdmin': True
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Contraseña incorrecta'
            }), 401
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== RUTA DE ESTADÍSTICAS ====================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Obtener estadísticas generales"""
    try:
        total_events = Event.query.count()
        total_gallery = GalleryItem.query.count()
        featured_events = Event.query.filter_by(featured=True).count()
        
        return jsonify({
            'status': 'success',
            'stats': {
                'totalEvents': total_events,
                'totalGallery': total_gallery,
                'featuredEvents': featured_events
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== INICIALIZACIÓN ====================

def init_db():
    """Inicializar la base de datos"""
    with app.app_context():
        db.create_all()
        
        if not HeroSettings.query.first():
            hero_settings = HeroSettings(
                hero_video='',
                event_date='2025-08-10T06:00:00'
            )
            db.session.add(hero_settings)
        
        if not EventSetting.query.first():
            main_event = EventSetting(
                event_name='Media Maratón de Quibdó 2025',
                event_date=datetime(2025, 8, 10, 6, 0, 0),
                is_active=True
            )
            db.session.add(main_event)
        
        db.session.commit()
        print("✅ Base de datos inicializada correctamente")

# ==================== MANEJO DE ERRORES ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'status': 'error', 'message': 'Recurso no encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'status': 'error', 'message': 'Error interno del servidor'}), 500

# ==================== EJECUTAR APP ====================

if __name__ == '__main__':
    init_db()
    print("🚀 Servidor Flask iniciado en http://localhost:5000")
    app.run(debug=True, port=5000, host='0.0.0.0')

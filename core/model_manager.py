import os
from core.paths import MODELS_DIR, EXTRA_MODEL_DIRS, ensure_dir

class ModelManager:
    @staticmethod
    def get_models_dir():
        ensure_dir(MODELS_DIR)
        return MODELS_DIR

    @staticmethod
    def get_search_dirs():
        """مجلد النماذج الأساسي (للتحميل) + مجلدات إضافية للقراءة فقط، مثل مجلد models بجانب البرنامج"""
        return [ModelManager.get_models_dir()] + [d for d in EXTRA_MODEL_DIRS if os.path.isdir(d)]

    RECOMMENDED = "deepdml/faster-whisper-large-v3-turbo-ct2"

    @staticmethod
    def recommend_model(ram_gb=None):
        """
        النموذج المناسب للجهاز. turbo دقته قريبة من large-v3 وأسرع منه بحوالي الضعف على المعالج،
        فهو الأنسب لأي جهاز فيه 4 جيجا ذاكرة أو أكثر. الأجهزة الأضعف: small.
        """
        if ram_gb is None:
            import psutil
            ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        return ModelManager.RECOMMENDED if ram_gb >= 4 else "small"

    @staticmethod
    def has_usable_model(settings):
        """هل يمكن التفريغ الآن بدون تحميل؟ (النموذج المختار موجود، أو مجلد نموذج مخصص صالح)"""
        custom = settings.get("local_model_path", "") or ""
        if custom and ModelManager.is_valid_model_dir(custom):
            return True
        return ModelManager.find_local_model(settings.get("model_size", ModelManager.RECOMMENDED)) is not None

    @staticmethod
    def to_repo_id(model_id):
        """تحويل الاسم المختصر (مثل large-v3) إلى اسم المستودع الكامل"""
        return model_id if "/" in model_id else f"Systran/faster-whisper-{model_id}"

    @staticmethod
    def folder_name_for(model_id):
        """اسم المجلد المعتمد لحفظ النموذج عند التحميل"""
        return ModelManager.to_repo_id(model_id).replace("/", "_")

    @staticmethod
    def _candidate_folder_names(model_id):
        """كل الأسماء المحتملة لمجلد النموذج، بما فيها الأسماء التي استخدمتها الإصدارات القديمة"""
        repo_id = ModelManager.to_repo_id(model_id)
        short_name = repo_id.split("/")[-1]
        names = [
            repo_id.replace("/", "_"),
            f"whisper-{short_name}",
        ]
        if "/" not in model_id:
            names.append(f"whisper-{model_id}")
        # إزالة التكرار مع الحفاظ على الترتيب
        return list(dict.fromkeys(names))

    @staticmethod
    def is_valid_model_dir(path):
        return os.path.isdir(path) and os.path.isfile(os.path.join(path, "model.bin"))

    @staticmethod
    def get_installed_models():
        installed = []
        for models_dir in ModelManager.get_search_dirs():
            for item in sorted(os.listdir(models_dir)):
                if item not in installed and ModelManager.is_valid_model_dir(os.path.join(models_dir, item)):
                    installed.append(item)
        return installed

    @staticmethod
    def find_local_model(model_id):
        """إرجاع مسار النموذج المحلي إن وُجد، أو None"""
        for models_dir in ModelManager.get_search_dirs():
            for name in ModelManager._candidate_folder_names(model_id):
                path = os.path.join(models_dir, name)
                if ModelManager.is_valid_model_dir(path):
                    return path
        return None

    @staticmethod
    def resolve_model_path(model_id):
        """المسار المحلي إن كان النموذج محملاً، وإلا اسم المستودع ليتم تحميله من الإنترنت"""
        return ModelManager.find_local_model(model_id) or ModelManager.to_repo_id(model_id)

    @staticmethod
    def get_installed_model_path(folder_name):
        """المسار الكامل لمجلد نموذج مثبت (يُستخدم في الحذف وعرض الحجم)"""
        name = os.path.basename(folder_name)
        for models_dir in ModelManager.get_search_dirs():
            path = os.path.join(models_dir, name)
            if os.path.isdir(path):
                return path
        return os.path.join(ModelManager.get_models_dir(), name)

    @staticmethod
    def get_folder_size(folder_path):
        total_size = 0
        if os.path.exists(folder_path):
            for dirpath, _, filenames in os.walk(folder_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp) and os.path.exists(fp):
                        total_size += os.path.getsize(fp)
        return total_size

    @staticmethod
    def extract_model_info(folder_name, i18n):
        unit_gb = i18n.get('unit_gb', 'GB')
        unit_mb = i18n.get('unit_mb', 'MB')
        unit_kb = i18n.get('unit_kb', 'KB')
        unit_b = i18n.get('unit_b', 'B')

        def format_size(size_bytes):
            if size_bytes >= 1024**3: return f"{size_bytes / 1024**3:.2f} {unit_gb}"
            elif size_bytes >= 1024**2: return f"{size_bytes / 1024**2:.2f} {unit_mb}"
            elif size_bytes >= 1024: return f"{size_bytes / 1024:.2f} {unit_kb}"
            return f"{int(size_bytes)} {unit_b}"

        folder_path = ModelManager.get_installed_model_path(folder_name)
        actual_size = ModelManager.get_folder_size(folder_path)

        info = {
            "name": folder_name,
            "status": i18n.get("dl_val_installed", "مثبت"),
            "size_str": format_size(actual_size) if actual_size > 0 else i18n.get("dl_val_unknown_size", "غير محدد")
        }
        return info

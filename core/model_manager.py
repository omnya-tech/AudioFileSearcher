import os

class ModelManager:
    @staticmethod
    def get_models_dir():
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        models_dir = os.path.join(base_dir, "models")
        if not os.path.exists(models_dir):
            try:
                os.makedirs(models_dir)
            except Exception:
                pass
        return models_dir

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
        models_dir = ModelManager.get_models_dir()
        installed = []
        if os.path.exists(models_dir):
            for item in sorted(os.listdir(models_dir)):
                if ModelManager.is_valid_model_dir(os.path.join(models_dir, item)):
                    installed.append(item)
        return installed

    @staticmethod
    def find_local_model(model_id):
        """إرجاع مسار النموذج المحلي إن وُجد، أو None"""
        models_dir = ModelManager.get_models_dir()
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
        """المسار الكامل لمجلد نموذج مثبت (يُستخدم في الحذف)"""
        return os.path.join(ModelManager.get_models_dir(), os.path.basename(folder_name))

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

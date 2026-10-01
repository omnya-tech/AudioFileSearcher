import os
import json
import re

def extract_keys_from_code(base_dir):
    """البحث في كل ملفات بايثون واستخراج المفاتيح المطلوبة للترجمة"""
    keys = set()
    # تعبير نمطي (Regex) للبحث عن أي استدعاء لـ i18n.get('key') أو اختصاراتها g('key') و add_row('key')
    pattern = re.compile(r'(?:i18n\.get|\bg|\badd_row)\(\s*["\']([a-z0-9_]+)["\']')
    
    for root, _, files in os.walk(base_dir):
        # استثناء مجلدات البيئة الوهمية إذا كانت موجودة
        if 'venv' in root or '.git' in root or '__pycache__' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = pattern.findall(content)
                        keys.update(matches)
                except Exception as e:
                    print(f"Error reading {file}: {e}")
                    
    return keys

def analyze_json(json_path, code_keys):
    """مقارنة المفاتيح الموجودة في الكود مع ملف الجيسون"""
    if not os.path.exists(json_path):
        print(f"\n[خطأ] ملف {os.path.basename(json_path)} غير موجود!")
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        json_keys = set(data.keys())
        
        missing_in_json = code_keys - json_keys
        unused_in_json = json_keys - code_keys
        
        print(f"\n{'='*40}")
        print(f" 📊 تقرير ملف: {os.path.basename(json_path)}")
        print(f"{'='*40}")
        
        print(f"\n❌ مفاتيح ناقصة (مستخدمة في الكود وغير موجودة في ملف {os.path.basename(json_path)}): {len(missing_in_json)}")
        for k in sorted(missing_in_json):
            print(f"   \"{k}\": \"\",")
            
        print(f"\n⚠️ مفاتيح زائدة (موجودة في ملف {os.path.basename(json_path)} وغير مستخدمة في الكود): {len(unused_in_json)}")
        for k in sorted(unused_in_json):
            print(f"   - {k}")
            
    except Exception as e:
        print(f"Error analyzing {json_path}: {e}")

if __name__ == "__main__":
    # مسار المشروع الأساسي
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("جاري فحص أكواد المشروع واستخراج المفاتيح...\n")
    code_keys = extract_keys_from_code(base_dir)
    print(f"✅ تم العثور على {len(code_keys)} مفتاح لغة مستخدم في الأكواد.")
    
    ar_path = os.path.join(base_dir, 'locales', 'ar.json')
    en_path = os.path.join(base_dir, 'locales', 'en.json')
    
    analyze_json(ar_path, code_keys)
    analyze_json(en_path, code_keys)
    
    print("\n" + "="*40)
    print("💡 نصيحة: انسخ المفاتيح الناقصة وأضفها لملف الـ JSON الخاص بك.")
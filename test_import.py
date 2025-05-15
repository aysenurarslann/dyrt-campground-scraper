# test_import.py
try:
    import asyncpg
    print("asyncpg başarıyla import edildi!")
    print(f"asyncpg sürümü: {asyncpg.__version__}")
except ImportError as e:
    print(f"Import hatası: {e}")
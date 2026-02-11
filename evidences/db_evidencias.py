"""
📊 EVIDENCIAS DE BASE DE DATOS - PostgreSQL
============================================

Este script consulta la base de datos y genera evidencias visuales
de que los datos se están guardando correctamente.

Ejecutar: python db_evidencias.py
"""

import asyncio
import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select, func
from tabulate import tabulate
import json

# Colores para terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_section(title):
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{title}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

# Configuración
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:admin123@localhost:5432/inventario_db"
)

async def get_db_session():
    """Crear sesión de base de datos"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

async def test_connection():
    """Probar conexión a la base de datos"""
    print_section("🔌 TEST DE CONEXIÓN")
    
    try:
        engine = create_async_engine(DATABASE_URL, echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            version = result.scalar()
            
            print(f"{Colors.OKGREEN}✅ Conexión exitosa{Colors.ENDC}")
            print(f"📍 URL: {DATABASE_URL.split('@')[1]}")  # Ocultar credenciales
            print(f"🐘 PostgreSQL Version:\n   {version[:80]}...")
            
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"{Colors.FAIL}❌ Error de conexión: {e}{Colors.ENDC}")
        return False

async def show_tables():
    """Mostrar todas las tablas"""
    print_section("📋 TABLAS EN LA BASE DE DATOS")
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        # Consultar tablas
        result = await conn.execute(text("""
            SELECT table_name, 
                   (SELECT COUNT(*) 
                    FROM information_schema.columns 
                    WHERE table_name = t.table_name) as num_columns
            FROM information_schema.tables t
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))
        
        tables = result.fetchall()
        
        # Formatear para mostrar
        table_data = []
        for i, (table_name, num_cols) in enumerate(tables, 1):
            # Contar registros
            count_result = await conn.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")
            )
            count = count_result.scalar()
            
            table_data.append([
                i,
                table_name,
                num_cols,
                count,
                "✅" if count > 0 else "⚠️"
            ])
        
        print(tabulate(
            table_data,
            headers=["#", "Tabla", "Columnas", "Registros", "Estado"],
            tablefmt="grid"
        ))
        
    await engine.dispose()

async def show_products():
    """Mostrar productos guardados"""
    print_section("📦 PRODUCTOS REGISTRADOS")
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        # Consultar últimos 10 productos
        result = await conn.execute(text("""
            SELECT 
                id,
                name,
                brand,
                size,
                barcode,
                TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') as created
            FROM products
            ORDER BY created_at DESC
            LIMIT 10;
        """))
        
        products = result.fetchall()
        
        if products:
            product_data = []
            for p in products:
                product_data.append([
                    p[0],  # id
                    p[1][:30] + "..." if len(p[1]) > 30 else p[1],  # name
                    p[2][:15] + "..." if p[2] and len(p[2]) > 15 else p[2],  # brand
                    p[3],  # size
                    p[4] if p[4] else "N/A",  # barcode
                    p[5]  # created
                ])
            
            print(tabulate(
                product_data,
                headers=["ID", "Nombre", "Marca", "Tamaño", "Barcode", "Creado"],
                tablefmt="grid"
            ))
            
            print(f"\n{Colors.OKGREEN}Total de productos: {len(products)}{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}⚠️ No hay productos registrados aún{Colors.ENDC}")
    
    await engine.dispose()

async def show_batches():
    """Mostrar lotes (batches) de productos"""
    print_section("📊 LOTES DE PRODUCTOS")
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT 
                pb.id,
                p.name,
                pb.batch_number,
                pb.stock_quantity,
                TO_CHAR(pb.expiry_date, 'YYYY-MM-DD') as expiry,
                pb.price
            FROM product_batches pb
            JOIN products p ON pb.product_id = p.id
            ORDER BY pb.created_at DESC
            LIMIT 10;
        """))
        
        batches = result.fetchall()
        
        if batches:
            batch_data = []
            for b in batches:
                batch_data.append([
                    b[0],  # id
                    b[1][:35] + "..." if len(b[1]) > 35 else b[1],  # product name
                    b[2] if b[2] else "N/A",  # batch_number
                    b[3],  # stock
                    b[4] if b[4] else "N/A",  # expiry
                    f"S/ {b[5]:.2f}" if b[5] else "N/A"  # price
                ])
            
            print(tabulate(
                batch_data,
                headers=["ID", "Producto", "Lote", "Stock", "Vencimiento", "Precio"],
                tablefmt="grid"
            ))
            
            print(f"\n{Colors.OKGREEN}Total de lotes: {len(batches)}{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}⚠️ No hay lotes registrados aún{Colors.ENDC}")
    
    await engine.dispose()

async def show_ocr_logs():
    """Mostrar logs de OCR"""
    print_section("🔍 LOGS DE OCR")
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT 
                id,
                image_path,
                confidence,
                ocr_engine,
                TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') as created
            FROM ocr_logs
            ORDER BY created_at DESC
            LIMIT 10;
        """))
        
        logs = result.fetchall()
        
        if logs:
            log_data = []
            for log in logs:
                # Truncar path
                paths = log[1].split(',')
                path_display = f"{len(paths)} imágenes"
                
                log_data.append([
                    log[0],  # id
                    path_display,
                    f"{log[2]:.2%}",  # confidence
                    log[3],  # engine
                    log[4]  # created
                ])
            
            print(tabulate(
                log_data,
                headers=["ID", "Imágenes", "Confianza", "Motor", "Fecha"],
                tablefmt="grid"
            ))
            
            # Calcular promedio de confianza
            avg_result = await conn.execute(text("""
                SELECT AVG(confidence) FROM ocr_logs;
            """))
            avg_confidence = avg_result.scalar()
            
            print(f"\n{Colors.OKGREEN}Confianza promedio: {avg_confidence:.2%}{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}⚠️ No hay logs de OCR aún{Colors.ENDC}")
    
    await engine.dispose()

async def show_statistics():
    """Mostrar estadísticas generales"""
    print_section("📈 ESTADÍSTICAS GENERALES")
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        # Total de productos
        result = await conn.execute(text("SELECT COUNT(*) FROM products"))
        total_products = result.scalar()
        
        # Total de lotes
        result = await conn.execute(text("SELECT COUNT(*) FROM product_batches"))
        total_batches = result.scalar()
        
        # Total stock
        result = await conn.execute(text("""
            SELECT COALESCE(SUM(stock_quantity), 0) FROM product_batches
        """))
        total_stock = result.scalar()
        
        # Productos con barcode
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM products WHERE barcode IS NOT NULL AND barcode != ''
        """))
        products_with_barcode = result.scalar()
        
        # OCR promedio
        result = await conn.execute(text("SELECT AVG(confidence) FROM ocr_logs"))
        avg_ocr = result.scalar()
        
        # Marcas únicas
        result = await conn.execute(text("""
            SELECT COUNT(DISTINCT brand) FROM products WHERE brand IS NOT NULL
        """))
        unique_brands = result.scalar()
        
        stats = [
            ["Total de productos", total_products, "✅"],
            ["Total de lotes", total_batches, "✅"],
            ["Stock total", total_stock, "✅"],
            ["Productos con barcode", f"{products_with_barcode}/{total_products}", "✅"],
            ["Confianza OCR promedio", f"{avg_ocr:.2%}" if avg_ocr else "N/A", "✅"],
            ["Marcas únicas", unique_brands, "✅"],
        ]
        
        print(tabulate(
            stats,
            headers=["Métrica", "Valor", "Estado"],
            tablefmt="grid"
        ))
        
        # Mostrar top 5 marcas
        print(f"\n{Colors.BOLD}🏆 TOP 5 MARCAS:{Colors.ENDC}")
        result = await conn.execute(text("""
            SELECT brand, COUNT(*) as count
            FROM products
            WHERE brand IS NOT NULL AND brand != ''
            GROUP BY brand
            ORDER BY count DESC
            LIMIT 5;
        """))
        
        top_brands = result.fetchall()
        if top_brands:
            for i, (brand, count) in enumerate(top_brands, 1):
                print(f"  {i}. {brand}: {count} productos")
        else:
            print(f"  {Colors.WARNING}No hay datos suficientes{Colors.ENDC}")
    
    await engine.dispose()

async def check_pgvector():
    """Verificar extensión PGVector"""
    print_section("🔢 PGVECTOR - Embeddings")
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        # Verificar extensión
        result = await conn.execute(text("""
            SELECT EXISTS(
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            );
        """))
        has_vector = result.scalar()
        
        if has_vector:
            print(f"{Colors.OKGREEN}✅ Extensión PGVector instalada{Colors.ENDC}")
            
            # Verificar si hay columnas vector
            result = await conn.execute(text("""
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE data_type = 'USER-DEFINED' AND udt_name = 'vector'
                LIMIT 5;
            """))
            
            vector_columns = result.fetchall()
            
            if vector_columns:
                print(f"\n{Colors.BOLD}Columnas con vectores:{Colors.ENDC}")
                for table, column in vector_columns:
                    print(f"  • {table}.{column}")
            else:
                print(f"\n{Colors.WARNING}⚠️ No se encontraron columnas de tipo vector{Colors.ENDC}")
                print(f"Esto es normal si estás usando ChromaDB/Pinecone externo")
        else:
            print(f"{Colors.WARNING}⚠️ Extensión PGVector no instalada{Colors.ENDC}")
            print(f"Ejecutar: CREATE EXTENSION IF NOT EXISTS vector;")
    
    await engine.dispose()

async def export_sample_data():
    """Exportar datos de ejemplo a JSON"""
    print_section("💾 EXPORTAR DATOS DE MUESTRA")
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        # Exportar un producto completo con su batch
        result = await conn.execute(text("""
            SELECT 
                p.id,
                p.name,
                p.brand,
                p.size,
                p.barcode,
                p.presentation,
                pb.batch_number,
                pb.expiry_date,
                pb.price,
                pb.stock_quantity
            FROM products p
            LEFT JOIN product_batches pb ON p.id = pb.product_id
            LIMIT 1;
        """))
        
        sample = result.fetchone()
        
        if sample:
            data = {
                "producto": {
                    "id": sample[0],
                    "nombre": sample[1],
                    "marca": sample[2],
                    "tamaño": sample[3],
                    "barcode": sample[4],
                    "presentacion": sample[5],
                },
                "lote": {
                    "numero_lote": sample[6],
                    "vencimiento": str(sample[7]) if sample[7] else None,
                    "precio": float(sample[8]) if sample[8] else None,
                    "stock": sample[9],
                }
            }
            
            filename = f"sample_product_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"{Colors.OKGREEN}✅ Datos exportados a: {filename}{Colors.ENDC}")
            print(f"\n{Colors.BOLD}Vista previa:{Colors.ENDC}")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"{Colors.WARNING}⚠️ No hay datos para exportar{Colors.ENDC}")
    
    await engine.dispose()

async def main():
    """Ejecutar todas las consultas de evidencia"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("=" * 80)
    print("📊 EVIDENCIAS DE BASE DE DATOS - POSTGRESQL")
    print("=" * 80)
    print(f"{Colors.ENDC}\n")
    
    # Test de conexión
    connected = await test_connection()
    
    if not connected:
        print(f"\n{Colors.FAIL}❌ No se pudo conectar a la base de datos{Colors.ENDC}")
        print(f"Verifica:")
        print(f"  1. PostgreSQL está corriendo")
        print(f"  2. DATABASE_URL es correcta")
        print(f"  3. Las credenciales son válidas")
        return
    
    # Mostrar evidencias
    await show_tables()
    await show_products()
    await show_batches()
    await show_ocr_logs()
    await show_statistics()
    await check_pgvector()
    await export_sample_data()
    
    # Resumen final
    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("=" * 80)
    print("✅ EVIDENCIAS GENERADAS EXITOSAMENTE")
    print("=" * 80)
    print(f"{Colors.ENDC}\n")
    
    print(f"{Colors.BOLD}💡 CÓMO MOSTRAR:{Colors.ENDC}")
    print("  1. Ejecutar: python db_evidencias.py")
    print("  2. Capturar screenshot de la terminal")
    print("  3. Abrir PgAdmin/DBeaver y mostrar datos visualmente")
    print("  4. Mostrar archivo JSON exportado")
    print("  5. Explicar cada tabla y su propósito")

if __name__ == "__main__":
    # Instalar dependencias si no están
    try:
        import tabulate
    except ImportError:
        print("Instalando tabulate...")
        os.system("pip install tabulate")
    
    asyncio.run(main())

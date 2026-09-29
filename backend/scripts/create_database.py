"""
Simple script to create database and run schema.sql
Run this first before setup_database.py
"""

import sys
import os
from pathlib import Path
import pymysql

# Add parent directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
# Load .env from backend dir so it works when run from project root
load_dotenv(backend_dir / ".env")
load_dotenv()  # Also allow cwd .env override

# Get database config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "12345")
DB_NAME = os.getenv("DB_NAME", "cancer_diagnosis_db")
DB_PORT = int(os.getenv("DB_PORT", 3306))

def create_database():
    """
    Create database and run schema.sql
    """
    print("="*60)
    print("🗄️  Creating Database")
    print("="*60)
    
    try:
        # Step 1: Connect to MySQL (without database)
        print("\n1️⃣  Connecting to MySQL...")
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        print("✅ Connected to MySQL")
        
        # Step 2: Create database
        print(f"\n2️⃣  Creating database '{DB_NAME}'...")
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"✅ Database '{DB_NAME}' created/verified")
        
        connection.close()
        
        # Step 3: Read and execute schema.sql
        print(f"\n3️⃣  Running schema.sql...")
        project_root = Path(__file__).parent.parent.parent
        schema_file = project_root / "database" / "schema.sql"
        
        if not schema_file.exists():
            print(f"❌ Schema file not found: {schema_file}")
            return False
        
        # Try using MySQL command line first (most reliable)
        import subprocess
        import shutil
        
        mysql_cmd = shutil.which('mysql')
        mysql_success = False
        
        if mysql_cmd:
            print("   Trying MySQL command line (most reliable)...")
            try:
                # Read schema file
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema_content = f.read()
                
                # Build mysql command - use environment variable for password to avoid warnings
                env = os.environ.copy()
                env['MYSQL_PWD'] = DB_PASSWORD
                
                mysql_command = [
                    mysql_cmd,
                    f'-h{DB_HOST}',
                    f'-P{str(DB_PORT)}',
                    f'-u{DB_USER}',
                    DB_NAME
                ]
                
                # Execute via mysql command
                result = subprocess.run(
                    mysql_command,
                    input=schema_content,
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=30
                )
                
                if result.returncode == 0:
                    print("✅ Schema.sql executed successfully via MySQL command")
                    mysql_success = True
                else:
                    error_output = result.stderr or result.stdout
                    print(f"   ⚠️  MySQL command had issues: {error_output[:300]}")
                    print("   Will try Python execution as fallback...")
            except Exception as e:
                print(f"   ⚠️  Could not use MySQL command: {str(e)}")
                print("   Will try Python execution as fallback...")
        else:
            print("   MySQL command not found, using Python execution...")
        
        # Fallback: Python execution if MySQL command didn't work
        if not mysql_success:
            print("   Using Python pymysql execution...")
            connection = pymysql.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                port=DB_PORT,
                autocommit=False
            )
            
            # Read schema file
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_content = f.read()
            
            # Process: remove CREATE DATABASE and USE, keep everything else
            lines = []
            for line in schema_content.split('\n'):
                line_upper = line.upper().strip()
                # Skip CREATE DATABASE and USE statements
                if 'CREATE DATABASE' in line_upper or line_upper.startswith('USE'):
                    continue
                lines.append(line)
            
            processed_sql = '\n'.join(lines)
            
            # Execute using pymysql's execute with multi-statements
            try:
                with connection.cursor() as cursor:
                    # Execute all statements at once
                    for statement in processed_sql.split(';'):
                        statement = statement.strip()
                        if statement and len(statement) > 10:  # Skip empty/short statements
                            try:
                                cursor.execute(statement)
                            except Exception as e:
                                error_msg = str(e)
                                # Only show non-ignorable errors
                                if "already exists" not in error_msg.lower() and "duplicate" not in error_msg.lower():
                                    print(f"   ⚠️  Warning: {error_msg[:100]}")
                
                connection.commit()
                print("✅ Schema.sql executed via Python")
            except Exception as e:
                print(f"   ⚠️  Python execution error: {str(e)}")
            finally:
                connection.close()
        
        # Step 4: Verify
        print(f"\n4️⃣  Verifying database...")
        try:
            connection = pymysql.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                port=DB_PORT
            )
            
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                table_names = [t[0] for t in tables]
                
                if len(tables) > 0:
                    print(f"✅ Found {len(tables)} tables: {', '.join(table_names)}")
                    
                    # Check users table if it exists
                    if 'users' in table_names:
                        try:
                            cursor.execute("SELECT COUNT(*) FROM users")
                            user_count = cursor.fetchone()[0]
                            print(f"✅ Found {user_count} users in database")
                        except Exception as e:
                            print(f"   ⚠️  Could not count users: {str(e)}")
                else:
                    print("❌ No tables found in database!")
                    print("   This means schema.sql did not execute correctly.")
                    print("   Please check the SQL file and try again.")
                    connection.close()
                    return False
            
            connection.close()
            
            print("\n" + "="*60)
            print("✅ Database created successfully!")
            print("="*60)
            return True
            
        except Exception as e:
            print(f"❌ Verification failed: {str(e)}")
            return False
        
    except pymysql.Error as e:
        print(f"\n❌ MySQL Error: {e}")
        print(f"   Please check:")
        print(f"   - MySQL is running")
        print(f"   - Credentials in .env file are correct")
        print(f"   - User '{DB_USER}' has CREATE DATABASE privileges")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_database()
    if not success:
        sys.exit(1)

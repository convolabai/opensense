#!/usr/bin/env python3
"""
Fix the channel_type column constraint in the subscriptions table.

This script removes the NOT NULL constraint from the channel_type column
to match the SQLAlchemy model definition.
"""

import os
import sys
import structlog
from sqlalchemy import create_engine, text

# Add the project root to the path
sys.path.append('/workspaces/langhook')

from langhook.subscriptions.config import subscription_settings

logger = structlog.get_logger("fix_channel_type")

def fix_channel_type_constraint():
    """Remove NOT NULL constraint from channel_type column."""
    try:
        # Create engine
        engine = create_engine(subscription_settings.postgres_dsn)
        
        with engine.connect() as conn:
            # Start a transaction
            trans = conn.begin()
            
            try:
                # Check current column definition
                check_sql = text("""
                    SELECT column_name, is_nullable, data_type
                    FROM information_schema.columns 
                    WHERE table_name='subscriptions' AND column_name='channel_type'
                """)
                result = conn.execute(check_sql).fetchone()
                
                if result:
                    print(f"Current channel_type column: nullable={result[1]}, type={result[2]}")
                    
                    if result[1] == 'NO':  # NOT NULL constraint exists
                        print("Removing NOT NULL constraint from channel_type column...")
                        
                        # Remove NOT NULL constraint
                        alter_sql = text("""
                            ALTER TABLE subscriptions 
                            ALTER COLUMN channel_type DROP NOT NULL
                        """)
                        conn.execute(alter_sql)
                        
                        print("Successfully removed NOT NULL constraint from channel_type column")
                    else:
                        print("channel_type column is already nullable")
                else:
                    print("channel_type column not found!")
                
                # Commit the transaction
                trans.commit()
                
            except Exception as e:
                # Rollback on error
                trans.rollback()
                raise e
                
    except Exception as e:
        logger.error(f"Failed to fix channel_type constraint: {e}")
        raise

if __name__ == "__main__":
    print("Fixing channel_type constraint in subscriptions table...")
    fix_channel_type_constraint()
    print("Done!")

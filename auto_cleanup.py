#!/usr/bin/env python3
"""
Автоматическая очистка без подтверждений (для скриптов)
"""

import asyncio
import sys
from cleanup import CleanupService

async def main():
    """Автоматическая очистка"""
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        cleanup = CleanupService()
        await cleanup.full_cleanup()
        print("✅ Автоматическая очистка завершена")
    else:
        print("❌ Используйте --force для автоматической очистки")
        print("⚠️  ВНИМАНИЕ: Это удалит ВСЕ данные без подтверждения!")

if __name__ == "__main__":
    asyncio.run(main())
-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_Task" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "filename" TEXT NOT NULL,
    "filePath" TEXT NOT NULL,
    "duration" REAL,
    "progress" REAL NOT NULL DEFAULT 0.0,
    "lastPlayedChunkIndex" INTEGER NOT NULL DEFAULT 0,
    "message" TEXT,
    "result" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);
INSERT INTO "new_Task" ("createdAt", "duration", "filePath", "filename", "id", "message", "progress", "result", "status", "updatedAt") SELECT "createdAt", "duration", "filePath", "filename", "id", "message", "progress", "result", "status", "updatedAt" FROM "Task";
DROP TABLE "Task";
ALTER TABLE "new_Task" RENAME TO "Task";
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;

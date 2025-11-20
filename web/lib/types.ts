// lib/types.ts
import { Prisma } from '@prisma/client';

export type Task = {
  id: string;
  title: string;
  audioUrl: string;
  duration: number;
  createdAt: Date;
};

export type Chunk = {
  id: string;
  taskId: string;
  index: number;
  startTime: number;
  endTime: number;
  text: string;
};

// 复合类型：包含 Chunks 的 Task，用于练习页面
// export type TaskWithChunks = Prisma.TaskGetPayload<{
//   include: { chunks: true }
// }>;

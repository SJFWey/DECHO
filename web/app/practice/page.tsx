"use client";

import { useEffect, useState } from "react";
import { api, Task } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Loader2, Mic } from "lucide-react";

export default function PracticePage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const data = await api.getTasks();
        // Filter for completed tasks only, as you can only practice on processed audio
        setTasks(data.filter((t) => t.status === "completed"));
      } catch (error) {
        console.error("Failed to fetch tasks", error);
      } finally {
        setLoading(false);
      }
    };

    fetchTasks();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Practice</h1>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {tasks.map((task) => (
          <Card key={task.task_id}>
            <CardHeader>
              <CardTitle className="truncate" title={task.file_path}>
                {task.file_path?.split(/[/\\]/).pop() || "Unknown File"}
              </CardTitle>
              <CardDescription>
                Ready for practice
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex justify-end space-x-2">
                <Link href={`/tasks/${task.task_id}?mode=practice`}>
                  <Button variant="default" size="sm">
                    <Mic className="mr-2 h-4 w-4" />
                    Start Practice
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ))}

        {tasks.length === 0 && (
          <div className="col-span-full text-center py-10 text-muted-foreground">
            No completed tasks found for practice. Upload and process a file first.
          </div>
        )}
      </div>
    </div>
  );
}

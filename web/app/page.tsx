"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, Task } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Upload, Loader2, Mic, Download, FileText, FileJson, FileType, Trash2 } from "lucide-react";

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loadingTasks, setLoadingTasks] = useState(true);
  const router = useRouter();

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    try {
      const data = await api.listTasks();
      // Sort by created_at desc
      const sorted = data.sort((a, b) => {
        const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return dateB - dateA;
      });
      setTasks(sorted);
    } catch (error) {
      console.error("Failed to fetch tasks", error);
      toast.error("Failed to load tasks");
    } finally {
      setLoadingTasks(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    try {
      setUploading(true);
      const task = await api.upload(file);
      toast.success("File uploaded successfully");
      setFile(null);
      // Refresh list
      fetchTasks();
      // Optionally start processing immediately
      try {
        await api.process(task.task_id);
        toast.info("Processing started");
        fetchTasks();
      } catch (e) {
        console.error("Auto-process failed", e);
      }
    } catch (error) {
      console.error(error);
      toast.error("Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const formatDuration = (seconds?: number) => {
    if (seconds === undefined || seconds === null) return "-";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}s`;
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleString(undefined, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const handleDownloadAudio = (task: Task) => {
    if (!task.file_path) return;
    const filename = task.file_path.split(/[\\/]/).pop();
    const url = `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/uploads/${filename}`;
    window.open(url, "_blank");
  };

  const handleDownloadSubtitle = async (task: Task, format: 'srt' | 'json') => {
    if (task.status !== 'completed') {
      toast.error("Task not completed yet");
      return;
    }
    
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';
    
    if (format === 'srt') {
       const url = `${baseUrl}/audio/download/${task.task_id}/srt`;
       window.open(url, "_blank");
    } else {
       try {
         const res = await api.getResult(task.task_id);
         const blob = new Blob([JSON.stringify(res, null, 2)], { type: "application/json" });
         const url = URL.createObjectURL(blob);
         const a = document.createElement("a");
         a.href = url;
         a.download = `subtitle_${task.task_id}.json`;
         document.body.appendChild(a);
         a.click();
         document.body.removeChild(a);
         URL.revokeObjectURL(url);
       } catch (e) {
         toast.error("Failed to download JSON");
       }
    }
  };

  const handleDeleteTask = async (task: Task) => {
    try {
      await api.deleteTask(task.task_id);
      toast.success("Task deleted successfully");
      fetchTasks();
    } catch (error) {
      console.error("Failed to delete task", error);
      toast.error("Failed to delete task");
    }
  };

  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* Upload Section */}
      <Card>
        <CardHeader>
          <CardTitle>Upload New Task</CardTitle>
          <CardDescription>Upload an audio file to start practicing.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-end gap-4">
            <div className="grid w-full max-w-sm items-center gap-1.5">
              <Label htmlFor="audio">Audio File</Label>
              <Input
                id="audio"
                type="file"
                accept="audio/*"
                onChange={handleFileChange}
              />
            </div>
            <Button onClick={handleUpload} disabled={!file || uploading}>
              {uploading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Task List Section */}
      <Card>
        <CardHeader>
          <CardTitle>Uploaded Tasks</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingTasks ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : tasks.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No tasks found. Upload one to get started.
            </div>
          ) : (
            <div className="relative w-full overflow-auto">
              <table className="w-full caption-bottom text-sm">
                <thead className="[&_tr]:border-b">
                  <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                    <th className="h-12 px-4 text-center align-middle font-medium text-muted-foreground">Filename</th>
                    <th className="h-12 px-4 text-center align-middle font-medium text-muted-foreground">Duration</th>
                    <th className="h-12 px-4 text-center align-middle font-medium text-muted-foreground">Uploaded At</th>
                    <th className="h-12 px-4 text-center align-middle font-medium text-muted-foreground">Status</th>
                    <th className="h-12 px-4 text-center align-middle font-medium text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody className="[&_tr:last-child]:border-0">
                  {tasks.map((task) => (
                    <tr
                      key={task.task_id}
                      className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted"
                    >
                      <td className="p-4 align-middle font-medium text-center">
                        {task.filename || task.file_path?.split(/[\\/]/).pop() || task.task_id}
                      </td>
                      <td className="p-4 align-middle text-center">{formatDuration(task.duration)}</td>
                      <td className="p-4 align-middle text-center">{formatDate(task.created_at)}</td>
                      <td className="p-4 align-middle capitalize text-center">{task.status}</td>
                      <td className="p-4 align-middle text-center">
                        <div className="flex justify-center items-center gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Practice"
                            onClick={() => router.push(`/practice/${task.task_id}`)}
                          >
                            <Mic className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Download Audio"
                            onClick={() => handleDownloadAudio(task)}
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                          
                                                    <SubtitleDownloadButton task={task} onDownload={handleDownloadSubtitle} />
                          
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Delete Task"
                            onClick={() => handleDeleteTask(task)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function SubtitleDownloadButton({ task, onDownload }: { task: Task, onDownload: (task: Task, format: 'srt' | 'json') => void }) {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div className="relative">
            <Button
                variant="ghost"
                size="icon"
                title="Download Subtitle"
                onClick={() => setIsOpen(!isOpen)}
            >
                <FileText className="h-4 w-4" />
            </Button>
            {isOpen && (
                <div className="absolute right-0 top-full mt-1 z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md animate-in fade-in-80 zoom-in-95">
                    <div 
                        className="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
                        onClick={() => { onDownload(task, 'srt'); setIsOpen(false); }}
                    >
                        <FileType className="mr-2 h-4 w-4" />
                        <span>SRT</span>
                    </div>
                    <div 
                        className="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
                        onClick={() => { onDownload(task, 'json'); setIsOpen(false); }}
                    >
                        <FileJson className="mr-2 h-4 w-4" />
                        <span>JSON</span>
                    </div>
                </div>
            )}
            {isOpen && (
                <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
            )}
        </div>
    )
}

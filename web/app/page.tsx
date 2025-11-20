"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { api, Task } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import { Loader2, Mic, Download, FileText, FileJson, FileType, Trash2, Play, MoreHorizontal, Settings } from "lucide-react";
import axios from "axios";
import { cn } from "@/lib/utils";
import Link from "next/link";

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loadingTasks, setLoadingTasks] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchTasks = async () => {
    try {
      const data = await api.listTasks();
      const sorted = data.sort((a, b) => {
        const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return dateB - dateA;
      });
      setTasks(sorted);
    } catch (error) {
      console.error("Failed to fetch tasks", error);
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
    if (!file) {
        fileInputRef.current?.click();
        return;
    }

    try {
      setUploading(true);
      const task = await api.upload(file);
      toast.success("File uploaded successfully");
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      
      fetchTasks();
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
    const hasTimezone = /[zZ]|[+\-]\d{2}:?\d{2}$/.test(dateString);
    const normalized = hasTimezone ? dateString : `${dateString}Z`;
    const date = new Date(normalized);
    if (isNaN(date.getTime())) return "-";
    return date.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  };

  const handleDownloadAudio = (task: Task) => {
    if (!task.file_path) return;
    const filename = task.file_path.split(/[\\/]/).pop();
    let baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    baseUrl = baseUrl.replace(/\/api\/?$/, "");
    const url = `${baseUrl}/uploads/${filename}`;
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
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        toast.success("Task already deleted");
        fetchTasks();
      } else {
        console.error("Failed to delete task", error);
        toast.error("Failed to delete task");
      }
    }
  };

  return (
    <div className="flex flex-col items-center w-full max-w-5xl px-4 space-y-12">
      
      {/* Settings Button */}
      <div className="fixed top-4 right-4 z-50">
        <Link href="/settings" className="p-2 rounded-full hover:bg-muted transition-colors text-muted-foreground hover:text-foreground block">
          <Settings className="w-5 h-5" />
        </Link>
      </div>

      {/* Hero / Title */}
      <div className="text-center space-y-4 mt-10">
        <h1 className="text-6xl font-bold tracking-tighter bg-gradient-to-r from-white to-white/60 bg-clip-text text-transparent">
          DECHO
        </h1>
      </div>

      {/* Upload Input (Google Search Style) */}
      <div className="w-full max-w-2xl relative group">
        <div 
            className={cn(
                "relative flex items-center w-full h-14 rounded-full bg-secondary/30 border border-white/10 backdrop-blur-md transition-all duration-300",
                "hover:bg-secondary/40 hover:shadow-[0_0_20px_rgba(255,255,255,0.05)] hover:border-white/20",
                "focus-within:bg-secondary/50 focus-within:shadow-[0_0_25px_rgba(255,255,255,0.1)] focus-within:border-white/30"
            )}
        >
            <input 
                type="file" 
                ref={fileInputRef}
                className="hidden" 
                accept="audio/*"
                onChange={handleFileChange}
            />
            
            <input 
                type="text"
                readOnly
                placeholder="Upload an audio file"
                value={file ? file.name : ""}
                onClick={() => fileInputRef.current?.click()}
                className="w-full h-full bg-transparent border-none outline-none px-8 text-lg placeholder:text-muted-foreground/50 cursor-pointer text-foreground"
            />

            {/* Upload Button */}
            <div className="absolute right-2 top-2 bottom-2 group/upload-btn">
                <div className="relative h-full rounded-full overflow-hidden p-[1px]">
                    {/* Default Border */}
                    <div className="absolute inset-0 bg-zinc-800 transition-opacity duration-300 group-hover/upload-btn:opacity-0" />
                    
                    {/* Rotating Gradient Border */}
                    <div className="absolute inset-[-100%] bg-[conic-gradient(from_90deg_at_50%_50%,#71717a_0%,#e4e4e7_50%,#71717a_100%)] animate-[spin_2s_linear_infinite] opacity-0 transition-opacity duration-300 group-hover/upload-btn:opacity-100" />
                    
                    <button 
                        onClick={(e) => {
                            e.stopPropagation();
                            handleUpload();
                        }}
                        disabled={uploading}
                        className="relative h-full px-6 rounded-full bg-background/90 hover:bg-background/70 text-white text-sm font-medium transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {uploading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            "Upload"
                        )}
                    </button>
                </div>
            </div>
        </div>
      </div>

      {/* Task Table */}
      <div className="w-full max-w-4xl space-y-4">
        {loadingTasks ? (
            <div className="flex justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground/50" />
            </div>
        ) : tasks.length > 0 && (
            <div className={cn(
                "w-full overflow-hidden rounded-2xl border border-white/5 bg-secondary/10 backdrop-blur-sm transition-all duration-300",
                "hover:shadow-[0_0_20px_rgba(255,255,255,0.05)] hover:border-white/10"
            )}>
                <table className="w-full text-sm text-left">
                    <thead className="text-xs uppercase text-muted-foreground/60 font-medium border-b border-white/5">
                        <tr>
                            <th className="px-6 py-4">Filename</th>
                            <th className="px-6 py-4 text-center">Duration</th>
                            <th className="px-6 py-4 text-center">Date</th>
                            <th className="px-6 py-4 text-center">Status</th>
                            <th className="px-6 py-4 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {tasks.map((task) => (
                            <tr 
                                key={task.task_id} 
                                className="group transition-all duration-300 hover:bg-white/5 hover:shadow-[0_0_15px_rgba(255,255,255,0.02)]"
                            >
                                <td className="px-6 py-4 font-medium text-foreground/90 truncate max-w-[200px]">
                                    {task.filename || "Untitled"}
                                </td>
                                <td className="px-6 py-4 text-center text-muted-foreground">
                                    {formatDuration(task.duration)}
                                </td>
                                <td className="px-6 py-4 text-center text-muted-foreground">
                                    {formatDate(task.created_at)}
                                </td>
                                <td className="px-6 py-4 text-center">
                                    <StatusBadge status={task.status} />
                                </td>
                                <td className="px-6 py-4 text-right">
                                    <div className="flex justify-end items-center gap-1">
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-8 w-8 rounded-full text-zinc-400 hover:bg-white/10 hover:text-blue-400 transition-colors"
                                            onClick={() => router.push(`/practice/${task.task_id}`)}
                                        >
                                            <Play className="h-4 w-4" />
                                        </Button>
                                        
                                        <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                                <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full text-zinc-400 hover:bg-white/10 hover:text-foreground transition-colors">
                                                    <MoreHorizontal className="h-4 w-4" />
                                                </Button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent align="end" className="bg-background/95 backdrop-blur-xl border-white/10">
                                                <DropdownMenuItem onClick={() => handleDownloadAudio(task)}>
                                                    <Download className="mr-2 h-4 w-4" /> Download Audio
                                                </DropdownMenuItem>
                                                <DropdownMenuItem onClick={() => handleDownloadSubtitle(task, 'srt')}>
                                                    <FileType className="mr-2 h-4 w-4" /> Download SRT
                                                </DropdownMenuItem>
                                                <DropdownMenuItem onClick={() => handleDownloadSubtitle(task, 'json')}>
                                                    <FileJson className="mr-2 h-4 w-4" /> Download JSON
                                                </DropdownMenuItem>
                                                <DropdownMenuItem 
                                                    onClick={() => handleDeleteTask(task)}
                                                    className="text-red-400 focus:text-red-400 focus:bg-red-400/10"
                                                >
                                                    <Trash2 className="mr-2 h-4 w-4" /> Delete
                                                </DropdownMenuItem>
                                            </DropdownMenuContent>
                                        </DropdownMenu>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
    const styles = {
        completed: "bg-green-500/10 text-green-400 border-green-500/20",
        processing: "bg-blue-500/10 text-blue-400 border-blue-500/20",
        pending: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
        failed: "bg-red-500/10 text-red-400 border-red-500/20",
    };
    
    const style = styles[status as keyof typeof styles] || "bg-gray-500/10 text-gray-400 border-gray-500/20";

    return (
        <span className={cn("px-2.5 py-0.5 rounded-full text-xs font-medium border", style)}>
            {status}
        </span>
    );
}


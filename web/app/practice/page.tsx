"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api, Task, Segment } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Play, Pause, Mic, ChevronLeft, ChevronRight, Volume2, ArrowLeft, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

function PracticeContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const id = searchParams.get("id");

  const [task, setTask] = useState<Task | null>(null);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [userRecordingUrl, setUserRecordingUrl] = useState<string | null>(null);
  const [isPlayingRecording, setIsPlayingRecording] = useState(false);
  const [showText, setShowText] = useState(true);
  const [inputValue, setInputValue] = useState("1");

  useEffect(() => {
    setInputValue((currentIndex + 1).toString());
  }, [currentIndex]);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const userAudioRef = useRef<HTMLAudioElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    if (!id) return;
    const init = async () => {
      try {
        const taskData = await api.getStatus(id);
        setTask(taskData);
        if (taskData.status === "completed") {
          const result = await api.getResult(id);
          setSegments(result.segments);
          
          // Load last played chunk or 0
          const initialIndex = taskData.last_played_chunk_index || 0;
          setCurrentIndex(initialIndex);
          
          // Load existing recording for initial segment if any
          loadRecording(initialIndex);
        } else {
          toast.error("Task is not ready for practice");
          router.push("/");
        }
      } catch (e) {
        console.error(e);
        toast.error("Failed to load task");
      }
    };
    init();
  }, [id, router]);

  const loadRecording = async (index: number) => {
    if (!id) return;
    try {
      const recordings = await api.getPracticeRecordings(id);
      // Find latest recording for this segment
      const segmentRecordings = recordings
        .filter(r => r.segmentIndex === index)
        .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
      
      if (segmentRecordings.length > 0) {
        const filename = segmentRecordings[0].filePath;
        let baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
        baseUrl = baseUrl.replace(/\/api\/?$/, "");
        setUserRecordingUrl(`${baseUrl}/user_recordings/${filename}`);
      } else {
        setUserRecordingUrl(null);
      }
    } catch (e) {
      console.error("Failed to load recordings", e);
    }
  };

  const getAudioUrl = () => {
    if (!task || !task.file_path) return "";
    const filename = task.file_path.split(/[\\/]/).pop();
    let baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    baseUrl = baseUrl.replace(/\/api\/?$/, "");
    return `${baseUrl}/uploads/${filename}`;
  };

  const handlePlayPause = () => {
    if (!audioRef.current || segments.length === 0) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      const segment = segments[currentIndex];
      // Only reset time if we're outside the current segment
      if (audioRef.current.currentTime < segment.start || audioRef.current.currentTime >= segment.end) {
        audioRef.current.currentTime = segment.start;
      }
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleTimeUpdate = () => {
    if (!audioRef.current || segments.length === 0) return;
    const segment = segments[currentIndex];
    if (audioRef.current.currentTime >= segment.end) {
      audioRef.current.pause();
      setIsPlaying(false);
      audioRef.current.currentTime = segment.start;
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0 && id) {
      const newIndex = currentIndex - 1;
      setCurrentIndex(newIndex);
      setIsPlaying(false);
      if (audioRef.current) {
        audioRef.current.pause();
      }
      loadRecording(newIndex);
      api.updateTaskProgress(id, newIndex);
    }
  };

  const handleNext = () => {
    if (currentIndex < segments.length - 1 && id) {
      const newIndex = currentIndex + 1;
      setCurrentIndex(newIndex);
      setIsPlaying(false);
      if (audioRef.current) {
        audioRef.current.pause();
      }
      loadRecording(newIndex);
      api.updateTaskProgress(id, newIndex);
    }
  };

  const handleJump = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setInputValue(value);
    const val = parseInt(value);
    if (!isNaN(val) && val >= 1 && val <= segments.length && id) {
      const newIndex = val - 1;
      if (newIndex !== currentIndex) {
        setCurrentIndex(newIndex);
        setIsPlaying(false);
        if (audioRef.current) {
          audioRef.current.pause();
        }
        loadRecording(newIndex);
        api.updateTaskProgress(id, newIndex);
      }
    }
  };

  const startRecording = async () => {
    if (!id) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const url = URL.createObjectURL(blob);
        setUserRecordingUrl(url); // Optimistic update
        
        // Upload
        try {
          await api.uploadPracticeRecording(id, currentIndex, blob);
          toast.success("Recording saved");
          loadRecording(currentIndex); // Reload to get server URL
        } catch (e) {
          toast.error("Failed to save recording");
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (e) {
      console.error(e);
      toast.error("Microphone access denied");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const playUserRecording = () => {
    if (!userAudioRef.current || !userRecordingUrl) return;
    
    if (isPlayingRecording) {
      userAudioRef.current.pause();
      setIsPlayingRecording(false);
    } else {
      userAudioRef.current.play();
      setIsPlayingRecording(true);
    }
  };

  if (!id) return <div>Missing Task ID</div>;

  if (!task || segments.length === 0) {
    return <div className="flex justify-center items-center h-screen">Loading...</div>;
  }

  const currentSegment = segments[currentIndex];

  return (
    <div className="flex flex-col items-center justify-center w-full min-h-[calc(100vh-4rem)] px-4 space-y-8 relative">
      
      {/* Back Button - Absolute Top Left */}
      <div className="absolute top-0 left-4">
        <Button 
            variant="ghost" 
            onClick={() => router.push("/")}
            className="text-muted-foreground hover:text-foreground transition-colors"
        >
            <ArrowLeft className="mr-2 h-4 w-4" /> Back
        </Button>
      </div>

      {/* Progress / Navigation & Toggle Text */}
      <div className="relative w-full max-w-5xl flex justify-center items-center">
        
        {/* Navigation */}
        <div className="flex items-center justify-center gap-8 w-full max-w-xl">
            <Button 
                variant="ghost" 
                size="icon" 
                onClick={handlePrev} 
                disabled={currentIndex === 0}
                className="hover:bg-white/5 rounded-full h-16 w-16 transition-all duration-200"
            >
            <ChevronLeft className="h-8 w-8" />
            </Button>
            
            <div className="flex items-baseline gap-2">
                <div className="relative group">
                    <input
                        value={inputValue}
                        onChange={handleJump}
                        className="w-24 text-center text-4xl font-bold bg-transparent border-none focus:outline-none p-0 text-foreground/90 group-hover:text-foreground transition-colors"
                    />
                    <div className="absolute bottom-0 left-0 w-full h-0.5 bg-white/10 scale-x-0 group-hover:scale-x-100 transition-transform duration-300" />
                </div>
                <span className="text-4xl text-muted-foreground/40 font-bold">/ {segments.length}</span>
            </div>

            <Button 
                variant="ghost" 
                size="icon" 
                onClick={handleNext} 
                disabled={currentIndex === segments.length - 1}
                className="hover:bg-white/5 rounded-full h-16 w-16 transition-all duration-200"
            >
            <ChevronRight className="h-8 w-8" />
            </Button>
        </div>

        {/* Toggle Text Button (Absolute Right) */}
        <div className="absolute right-0 top-1/2 -translate-y-1/2 group/toggle-btn h-10">
            <div className="relative h-full rounded-full overflow-hidden p-[1px]">
                {/* Default Border */}
                <div className="absolute inset-0 bg-zinc-800 transition-opacity duration-300 group-hover/toggle-btn:opacity-0" />
                
                {/* Rotating Gradient Border */}
                <div className="absolute inset-[-100%] bg-[conic-gradient(from_90deg_at_50%_50%,#71717a_0%,#e4e4e7_50%,#71717a_100%)] animate-[spin_2s_linear_infinite] opacity-0 transition-opacity duration-300 group-hover/toggle-btn:opacity-100" />
                
                <button 
                    onClick={() => setShowText(!showText)}
                    className="relative h-full px-4 rounded-full bg-background/90 hover:bg-background/70 text-white text-sm font-medium transition-all flex items-center gap-2"
                >
                    {showText ? (
                        <>
                            <EyeOff className="h-4 w-4" />
                            <span>Hide Text</span>
                        </>
                    ) : (
                        <>
                            <Eye className="h-4 w-4" />
                            <span>Show Text</span>
                        </>
                    )}
                </button>
            </div>
        </div>
      </div>

      {/* Text Display Card */}
      <div className={cn(
          "w-full max-w-5xl min-h-[300px] flex flex-col items-center justify-center p-12 rounded-3xl",
          "bg-secondary/10 backdrop-blur-md border border-white/5",
          "transition-all duration-500 hover:shadow-[0_0_30px_rgba(255,255,255,0.05)] hover:border-white/10"
      )}>
          <p className={cn(
            "text-3xl md:text-4xl font-medium leading-relaxed text-center text-foreground/90 transition-all duration-500",
            !showText && "blur-md select-none opacity-50"
          )}>
            {currentSegment.text}
          </p>
          {currentSegment.translation && (
            <p className={cn(
                "text-xl text-muted-foreground mt-8 text-center font-light transition-all duration-500",
                !showText && "blur-md select-none opacity-50"
            )}>
              {currentSegment.translation}
            </p>
          )}
      </div>

      {/* Controls */}
      <div className="flex items-center gap-8 mt-8">
        {/* Play/Pause Original */}
        <div className="relative group">
            <div className="absolute inset-0 bg-blue-500/20 rounded-full blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <Button
            size="lg"
            variant="outline"
            className={cn(
                "h-24 w-24 rounded-full border-2 border-white/10 bg-background/50 backdrop-blur-sm",
                "hover:border-blue-500/50 hover:bg-blue-500/10 hover:text-blue-400 transition-all duration-300",
                isPlaying && "border-blue-500 text-blue-400 shadow-[0_0_20px_rgba(59,130,246,0.3)]"
            )}
            onClick={handlePlayPause}
            >
            {isPlaying ? <Pause className="h-20 w-20" /> : <Play className="h-20 w-20 ml-1" />}
            </Button>
            <span className="absolute -bottom-8 left-1/2 -translate-x-1/2 text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">Listen</span>
        </div>

        {/* Record User */}
        <div className="relative group">
            <div className="absolute inset-0 bg-red-500/20 rounded-full blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <Button
            size="lg"
            variant="outline"
            className={cn(
                "h-24 w-24 rounded-full border-2 border-white/10 bg-background/50 backdrop-blur-sm",
                "hover:border-red-500/50 hover:bg-red-500/10 hover:text-red-400 transition-all duration-300",
                isRecording && "border-red-500 text-red-400 animate-pulse shadow-[0_0_30px_rgba(239,68,68,0.4)]"
            )}
            onClick={toggleRecording}
            >
            <Mic className="h-20 w-20" />
            </Button>
            <span className="absolute -bottom-8 left-1/2 -translate-x-1/2 text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">Record</span>
        </div>

        {/* Play User Recording */}
        <div className="relative group">
            <div className="absolute inset-0 bg-purple-500/20 rounded-full blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <Button
            size="lg"
            variant="outline"
            className={cn(
                "h-24 w-24 rounded-full border-2 border-white/10 bg-background/50 backdrop-blur-sm",
                "hover:border-purple-500/50 hover:bg-purple-500/10 hover:text-purple-400 transition-all duration-300",
                "disabled:opacity-30 disabled:hover:border-white/10 disabled:hover:bg-transparent",
                isPlayingRecording && "border-purple-500 text-purple-400 shadow-[0_0_20px_rgba(168,85,247,0.3)]"
            )}
            onClick={playUserRecording}
            disabled={!userRecordingUrl}
            >
            <Volume2 className="h-20 w-20" />
            </Button>
            <span className="absolute -bottom-8 left-1/2 -translate-x-1/2 text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">Replay</span>
        </div>
      </div>

      {/* Hidden Audio Elements */}
      <audio
        ref={audioRef}
        src={getAudioUrl()}
        onTimeUpdate={handleTimeUpdate}
        onEnded={() => setIsPlaying(false)}
      />
      <audio
        ref={userAudioRef}
        src={userRecordingUrl || undefined}
        onEnded={() => setIsPlayingRecording(false)}
      />
    </div>
  );
}

export default function PracticePage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <PracticeContent />
    </Suspense>
  );
}

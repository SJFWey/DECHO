"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, Task, Segment } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Play, Pause, Mic, ChevronLeft, ChevronRight, Volume2, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export default function PracticePage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [task, setTask] = useState<Task | null>(null);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [userRecordingUrl, setUserRecordingUrl] = useState<string | null>(null);
  const [isPlayingRecording, setIsPlayingRecording] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const userAudioRef = useRef<HTMLAudioElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    const init = async () => {
      try {
        const taskData = await api.getStatus(id);
        setTask(taskData);
        if (taskData.status === "completed") {
          const result = await api.getResult(id);
          setSegments(result.segments);
          
          // Load existing recording for first segment if any
          loadRecording(0);
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
    try {
      const recordings = await api.getPracticeRecordings(id);
      // Find latest recording for this segment
      const segmentRecordings = recordings
        .filter(r => r.segmentIndex === index)
        .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
      
      if (segmentRecordings.length > 0) {
        const filename = segmentRecordings[0].filePath;
        const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
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
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    return `${baseUrl}/uploads/${filename}`;
  };

  const handlePlayPause = () => {
    if (!audioRef.current || segments.length === 0) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      const segment = segments[currentIndex];
      audioRef.current.currentTime = segment.start;
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
    if (currentIndex > 0) {
      const newIndex = currentIndex - 1;
      setCurrentIndex(newIndex);
      setIsPlaying(false);
      loadRecording(newIndex);
    }
  };

  const handleNext = () => {
    if (currentIndex < segments.length - 1) {
      const newIndex = currentIndex + 1;
      setCurrentIndex(newIndex);
      setIsPlaying(false);
      loadRecording(newIndex);
    }
  };

  const startRecording = async () => {
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

  if (!task || segments.length === 0) {
    return <div className="flex justify-center items-center h-screen">Loading...</div>;
  }

  const currentSegment = segments[currentIndex];

  return (
    <div className="container mx-auto py-8 flex flex-col items-center min-h-screen max-w-2xl">
      <div className="w-full flex justify-start mb-4">
        <Button variant="ghost" onClick={() => router.push("/")}>
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Tasks
        </Button>
      </div>

      {/* Top: Navigation */}
      <div className="flex items-center justify-between w-full mb-8">
        <Button variant="outline" size="icon" onClick={handlePrev} disabled={currentIndex === 0}>
          <ChevronLeft className="h-6 w-6" />
        </Button>
        <div className="text-xl font-semibold">
          Chunk {currentIndex + 1} / {segments.length}
        </div>
        <Button variant="outline" size="icon" onClick={handleNext} disabled={currentIndex === segments.length - 1}>
          <ChevronRight className="h-6 w-6" />
        </Button>
      </div>

      {/* Center: Text */}
      <Card className="w-full mb-8 min-h-[200px] flex items-center justify-center">
        <CardContent className="p-8 text-center">
          <p className="text-2xl font-medium leading-relaxed">
            {currentSegment.text}
          </p>
          {currentSegment.translation && (
            <p className="text-lg text-muted-foreground mt-4">
              {currentSegment.translation}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Bottom: Controls */}
      <div className="flex items-center gap-8">
        {/* Play/Pause Original */}
        <Button
          size="lg"
          variant={isPlaying ? "default" : "outline"}
          className="h-16 w-16 rounded-full"
          onClick={handlePlayPause}
        >
          {isPlaying ? <Pause className="h-8 w-8" /> : <Play className="h-8 w-8" />}
        </Button>

        {/* Record User */}
        <Button
          size="lg"
          variant={isRecording ? "destructive" : "outline"}
          className={cn("h-16 w-16 rounded-full", isRecording && "animate-pulse")}
          onClick={toggleRecording}
        >
          <Mic className="h-8 w-8" />
        </Button>

        {/* Play User Recording */}
        <Button
          size="lg"
          variant={isPlayingRecording ? "secondary" : "outline"}
          className="h-16 w-16 rounded-full"
          onClick={playUserRecording}
          disabled={!userRecordingUrl}
        >
          <Volume2 className="h-8 w-8" />
        </Button>
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
        src={userRecordingUrl || ""}
        onEnded={() => setIsPlayingRecording(false)}
      />
    </div>
  );
}

"use client"

import { useEffect, useState, useRef, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import { api, Task, Segment } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { Play, Pause, Download, Mic, RefreshCw, Repeat, FileText } from "lucide-react"
import { cn } from "@/lib/utils"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { toast } from "sonner"

function TaskDetailsContent() {
  const searchParams = useSearchParams()
  const id = searchParams.get("id")
  const [task, setTask] = useState<Task | null>(null)
  const [segments, setSegments] = useState<Segment[]>([])
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState<number | null>(null)
  const audioRef = useRef<HTMLAudioElement>(null)
  
  // Practice Mode State
  const [isPracticeMode, setIsPracticeMode] = useState(searchParams.get("mode") === "practice")
  const [isLooping, setIsLooping] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [userRecordings, setUserRecordings] = useState<Record<number, string>>({})
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const userAudioRef = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    if (!id) return

    let interval: NodeJS.Timeout

    const fetchStatus = async () => {
      try {
        const data = await api.getStatus(id)
        setTask(data)

        if (data.status === "completed" && data.result) {
          setSegments(data.result.segments)
          clearInterval(interval)
        } else if (data.status === "failed") {
          clearInterval(interval)
        }
      } catch (error) {
        console.error("Failed to fetch status", error)
      }
    }

    fetchStatus()
    interval = setInterval(fetchStatus, 2000)

    return () => clearInterval(interval)
  }, [id])

  useEffect(() => {
    if (task?.status === 'completed' && id) {
      const fetchRecordings = async () => {
        try {
          const recs = await api.getPracticeRecordings(id)
          const recMap: Record<number, string> = {}
          recs.forEach(r => {
            recMap[r.segmentIndex] = r.filePath
          })
          setUserRecordings(recMap)
        } catch (e) {
          console.error(e)
        }
      }
      fetchRecordings()
    }
  }, [task?.status, id])

  const getAudioUrl = () => {
    if (!task || !task.file_path) return ""
    // task.file_path is like "output/uploads/uuid_filename.wav"
    // We need "uuid_filename.wav"
    const filename = task.file_path.split(/[/\\]/).pop()
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    return `${baseUrl}/uploads/${filename}`
  }

  const playSegment = (index: number) => {
    if (!audioRef.current || !segments[index]) return
    
    const segment = segments[index]
    audioRef.current.currentTime = segment.start
    audioRef.current.play()
    setCurrentSegmentIndex(index)
  }

  const handleTimeUpdate = () => {
    if (!audioRef.current || currentSegmentIndex === null) return
    
    const segment = segments[currentSegmentIndex]
    if (audioRef.current.currentTime >= segment.end) {
      if (isLooping && isPracticeMode) {
        audioRef.current.currentTime = segment.start
        audioRef.current.play()
      } else {
        audioRef.current.pause()
        setCurrentSegmentIndex(null)
      }
    }
  }

  const startRecording = async () => {
    if (!id) return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        if (currentSegmentIndex !== null) {
          try {
            const res = await api.uploadPracticeRecording(id, currentSegmentIndex, blob)
            setUserRecordings(prev => ({
              ...prev,
              [currentSegmentIndex]: res.filePath
            }))
            toast.success("Recording saved")
          } catch (err) {
            console.error("Failed to upload recording", err)
            toast.error("Failed to save recording")
          }
        }
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start()
      setIsRecording(true)
    } catch (err) {
      console.error("Failed to start recording", err)
      toast.error("Could not access microphone")
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const getUserAudioUrl = (filename: string) => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    return `${baseUrl}/user_recordings/${filename}`
  }

  if (!id) return <div className="p-8">Missing Task ID</div>
  if (!task) return <div className="p-8">Loading...</div>

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Task: {id}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>
                Status:{" "}
                {task.status === "failed" ? (
                  <span className="font-semibold text-red-500">Error</span>
                ) : (
                  <span className="font-semibold capitalize">{task.status}</span>
                )}
              </span>
              <span>{Math.round(task.progress * 100)}%</span>
            </div>
            <Progress value={task.progress * 100} />
            {task.message && <p className="text-red-500 text-sm">{task.message}</p>}
            
            {task.status === 'pending' && (
              <Button 
                className="w-full mt-4" 
                onClick={async () => {
                  try {
                    await api.process(id);
                    toast.info("Processing started");
                    // Force refresh status
                    const data = await api.getStatus(id);
                    setTask(data);
                  } catch (e) {
                    toast.error("Failed to start processing");
                  }
                }}
              >
                Start Processing
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {task.status === "completed" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="md:col-span-2">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle>Transcript</CardTitle>
              <div className="flex items-center space-x-2">
                <Switch 
                  id="practice-mode" 
                  checked={isPracticeMode}
                  onCheckedChange={setIsPracticeMode}
                />
                <Label htmlFor="practice-mode">Practice Mode</Label>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
                {segments.map((segment, index) => (
                  <div 
                    key={index}
                    className={cn(
                      "p-3 rounded-lg cursor-pointer hover:bg-muted transition-colors border",
                      currentSegmentIndex === index ? "bg-muted border-primary" : "border-transparent"
                    )}
                    onClick={() => playSegment(index)}
                  >
                    <div className="flex justify-between text-xs text-muted-foreground mb-1">
                      <span>{formatTime(segment.start)} - {formatTime(segment.end)}</span>
                    </div>
                    <p className="text-sm">{segment.text}</p>
                    {segment.translation && (
                      <p className="text-sm text-muted-foreground mt-1">{segment.translation}</p>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Player</CardTitle>
            </CardHeader>
            <CardContent>
              <audio 
                ref={audioRef} 
                src={getAudioUrl()} 
                controls 
                className="w-full mb-4"
                onTimeUpdate={handleTimeUpdate}
              />
              
              <div className="space-y-4">
                {isPracticeMode && (
                  <div className="p-4 border rounded-lg bg-muted/50 space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Practice Controls</span>
                      {currentSegmentIndex !== null && (
                        <span className="text-xs text-muted-foreground">
                          Segment {currentSegmentIndex + 1}
                        </span>
                      )}
                    </div>
                    
                    <div className="flex gap-2">
                      <Button 
                        variant={isLooping ? "default" : "outline"}
                        size="icon"
                        onClick={() => setIsLooping(!isLooping)}
                        title="Loop Segment"
                      >
                        <Repeat className="h-4 w-4" />
                      </Button>
                      
                      <Button
                        variant={isRecording ? "destructive" : "outline"}
                        size="icon"
                        onClick={isRecording ? stopRecording : startRecording}
                        disabled={currentSegmentIndex === null}
                        title="Record"
                      >
                        <Mic className="h-4 w-4" />
                      </Button>

                      {currentSegmentIndex !== null && userRecordings[currentSegmentIndex] && (
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => {
                            if (userAudioRef.current) {
                              userAudioRef.current.src = getUserAudioUrl(userRecordings[currentSegmentIndex])
                              userAudioRef.current.play()
                            }
                          }}
                          title="Play My Recording"
                          >
                          <Play className="h-4 w-4" />
                        </Button>
                      )}
                    </div>

                    <audio ref={userAudioRef} className="hidden" onEnded={() => {}} />
                  </div>
                )}

                <div className="space-y-2">
                  <Button className="w-full" variant="outline" onClick={() => window.open(getAudioUrl(), '_blank')}>
                    <Download className="mr-2 h-4 w-4" /> Download Audio
                  </Button>
                  <Button className="w-full" variant="outline" onClick={() => window.open(api.downloadSrtUrl(id), '_blank')}>
                    <FileText className="mr-2 h-4 w-4" /> Download SRT
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 1000)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')},${ms.toString().padStart(3, '0')}`
}

export default function TaskPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <TaskDetailsContent />
    </Suspense>
  )
}

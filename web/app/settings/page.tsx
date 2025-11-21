"use client"

import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { api, Config } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { toast } from "sonner"
import { Loader2, ArrowLeft } from "lucide-react"
import Link from "next/link"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

const VOICES = [
  "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede", 
  "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba", 
  "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar", 
  "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi", 
  "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat"
].sort();

export default function SettingsPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testingTTS, setTestingTTS] = useState(false)
  const { register, handleSubmit, setValue, watch, reset, getValues } = useForm<Config>()

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const config = await api.getConfig()
        reset(config)
      } catch (error) {
        console.error(error)
        toast.error("Failed to load settings")
      } finally {
        setLoading(false)
      }
    }
    fetchConfig()
  }, [reset])

  const onSubmit = async (data: Config) => {
    try {
      setSaving(true)
      // Remove max_split_length from app config to prevent overwriting config.yaml
      const configToUpdate = { ...data };
      if (configToUpdate.app) {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { max_split_length, ...restApp } = configToUpdate.app;
        configToUpdate.app = restApp as any;
      }

      await api.updateConfig(configToUpdate)
      toast.success("Settings saved")
    } catch (error) {
      console.error(error)
      toast.error("Failed to save settings")
    } finally {
      setSaving(false)
    }
  }

  const onTestConnection = async () => {
    try {
      setTesting(true)
      const data = getValues()
      await api.testConfig(data)
      toast.success("Connection successful")
    } catch (error: any) {
      console.error(error)
      const message = error.response?.data?.detail || "Connection failed"
      toast.error(message)
    } finally {
      setTesting(false)
    }
  }

  const onTestTTSConnection = async () => {
    try {
      setTestingTTS(true)
      const data = getValues()
      await api.testTTSConfig(data)
      toast.success("TTS Connection successful")
    } catch (error: any) {
      console.error(error)
      const message = error.response?.data?.detail || "TTS Connection failed"
      toast.error(message)
    } finally {
      setTestingTTS(false)
    }
  }

  if (loading) return <div className="p-8">Loading settings...</div>

  return (
    <div className="max-w-5xl mx-auto space-y-6 w-full px-4 py-8">
      <div className="flex items-center gap-4">
        <Link href="/">
          <Button variant="ghost" size="icon" className="rounded-full hover:bg-secondary/80">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <h1 className="text-2xl font-bold">Settings</h1>
      </div>
      
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">


        <Card>
          <CardHeader>
            <CardTitle>LLM Settings</CardTitle>
            <CardDescription>Configure Language Model for semantic splitting</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between mb-4">
              <Label htmlFor="use_llm">Use LLM for Segmentation</Label>
              <Switch 
                id="use_llm" 
                checked={watch("app.use_llm")}
                onCheckedChange={(checked) => setValue("app.use_llm", checked)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="target_language">Target Language</Label>
              <Select 
                onValueChange={(value) => setValue("app.target_language", value)}
                defaultValue={watch("app.target_language")}
                value={watch("app.target_language")}
              >
                <SelectTrigger id="target_language">
                  <SelectValue placeholder="Select language" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="de">German</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="api_key">API Key</Label>
              <Input id="api_key" type="password" {...register("llm.api_key")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="base_url">Base URL</Label>
              <Input id="base_url" {...register("llm.base_url")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="model">Model</Label>
              <Input id="model" {...register("llm.model")} placeholder="openai/gpt-4o" />
            </div>
            <Button 
              type="button" 
              variant="outline" 
              onClick={onTestConnection}
              disabled={testing}
            >
              {testing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Test Connection
            </Button>
          </CardContent>
        </Card>



        <Card>
          <CardHeader>
            <CardTitle>TTS Settings</CardTitle>
            <CardDescription>Configure Text-to-Speech</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="tts_api_key">API Key</Label>
              <Input id="tts_api_key" type="password" {...register("tts.api_key")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tts_model">Model</Label>
              <Input id="tts_model" {...register("tts.model")} placeholder="gemini-2.5-flash-preview-tts" />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="tts_language">Default Language</Label>
                  <Select 
                    onValueChange={(value) => setValue("tts.defaults.language", value)}
                    defaultValue={watch("tts.defaults.language")}
                    value={watch("tts.defaults.language")}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select language" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="en-US">English (US)</SelectItem>
                      <SelectItem value="de-DE">German (Germany)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tts_speed">Speed</Label>
                   <Input id="tts_speed" {...register("tts.defaults.speed")} placeholder="Native conversational pace" />
                </div>
            </div>

            <div className="space-y-2">
                <Label htmlFor="tts_tone">Tone</Label>
                <Input id="tts_tone" {...register("tts.defaults.tone")} placeholder="Clear, educational, engaging" />
            </div>

            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="tts_voice_male">Male Voice (Redner1)</Label>
                  <Select 
                    onValueChange={(value) => setValue("tts.voice_map.male", value)}
                    defaultValue={watch("tts.voice_map.male")}
                    value={watch("tts.voice_map.male")}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select voice" />
                    </SelectTrigger>
                    <SelectContent>
                        {VOICES.map(voice => (
                            <SelectItem key={voice} value={voice}>{voice}</SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tts_voice_female">Female Voice (Redner2)</Label>
                  <Select 
                    onValueChange={(value) => setValue("tts.voice_map.female", value)}
                    defaultValue={watch("tts.voice_map.female")}
                    value={watch("tts.voice_map.female")}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select voice" />
                    </SelectTrigger>
                    <SelectContent>
                        {VOICES.map(voice => (
                            <SelectItem key={voice} value={voice}>{voice}</SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>
            </div>

            <Button 
              type="button" 
              variant="outline" 
              onClick={onTestTTSConnection}
              disabled={testingTTS}
            >
              {testingTTS && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Test TTS Connection
            </Button>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button type="submit" disabled={saving}>
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Changes
          </Button>
        </div>
      </form>
    </div>
  )
}

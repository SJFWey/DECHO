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
import { Loader2 } from "lucide-react"

export default function SettingsPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
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
      await api.updateConfig(data)
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
    } catch (error) {
      console.error(error)
      toast.error("Connection failed")
    } finally {
      setTesting(false)
    }
  }

  if (loading) return <div className="p-8">Loading settings...</div>

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>
      
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>ASR Settings</CardTitle>
            <CardDescription>Configure Automatic Speech Recognition</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="enable_demucs">Enable Demucs (Voice Separation)</Label>
              <Switch 
                id="enable_demucs" 
                checked={watch("asr.enable_demucs")}
                onCheckedChange={(checked) => setValue("asr.enable_demucs", checked)}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="enable_vad">Enable VAD (Voice Activity Detection)</Label>
              <Switch 
                id="enable_vad" 
                checked={watch("asr.enable_vad")}
                onCheckedChange={(checked) => setValue("asr.enable_vad", checked)}
              />
            </div>
          </CardContent>
        </Card>

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
            <CardTitle>App Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="max_split_length">Max Split Length (chars)</Label>
              <Input 
                id="max_split_length" 
                type="number" 
                {...register("app.max_split_length", { valueAsNumber: true })} 
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="target_language">Target Language</Label>
              <Input id="target_language" {...register("app.target_language")} />
            </div>
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

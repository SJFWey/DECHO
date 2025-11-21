import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || (typeof window === 'undefined' ? 'http://127.0.0.1:8000/api' : '/api');
const API_URL = `${API_BASE_URL}/audio`;

export interface Task {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  file_path?: string;
  filename?: string;
  progress: number;
  last_played_chunk_index?: number;
  message?: string;
  duration?: number;
  created_at?: string;
  result?: {
    segments: Segment[];
    srt: string;
  };
}

export interface Segment {
  start: number;
  end: number;
  text: string;
  translation?: string;
}

export const api = {
  upload: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await axios.post<Task>(`${API_URL}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  process: async (taskId: string) => {
    const response = await axios.post<Task>(`${API_URL}/process/${taskId}`);
    return response.data;
  },

  getStatus: async (taskId: string) => {
    const response = await axios.get<Task>(`${API_URL}/status/${taskId}`);
    return response.data;
  },

  getResult: async (taskId: string) => {
    const response = await axios.get<{ task_id: string; segments: Segment[] }>(`${API_URL}/result/${taskId}`);
    return response.data;
  },

  listTasks: async () => {
    try {
      const response = await axios.get<Task[]>(`${API_URL}/tasks`);
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch tasks from ${API_URL}/tasks`, error);
      throw error;
    }
  },

  deleteTask: async (taskId: string) => {
    const response = await axios.delete(`${API_URL}/task/${taskId}`);
    return response.data;
  },

  getConfig: async () => {
    const response = await axios.get<Config>(`${API_BASE_URL}/config/`);
    return response.data;
  },

  updateConfig: async (config: Config) => {
    const response = await axios.patch<Config>(`${API_URL.replace('/audio', '/config')}`, config);
    return response.data;
  },

  testConfig: async (config: Config) => {
    const response = await axios.post<{ status: string; message: string }>(
      `${API_URL.replace('/audio', '/config')}/test-llm`,
      config
    );
    return response.data;
  },

  testTTSConfig: async (config: Config) => {
    const response = await axios.post<{ status: string; message: string }>(
      `${API_URL.replace('/audio', '/config')}/test-tts`,
      config
    );
    return response.data;
  },

  uploadPracticeRecording: async (taskId: string, segmentIndex: number, file: Blob) => {
    const formData = new FormData();
    formData.append('file', file, 'recording.webm');
    const response = await axios.post<{ message: string; filePath: string }>(
      `${API_URL}/practice/${taskId}/${segmentIndex}`,
      formData
    );
    return response.data;
  },

  getPracticeRecordings: async (taskId: string) => {
    const response = await axios.get<
      { id: string; segmentIndex: number; filePath: string; createdAt: string }[]
    >(`${API_URL}/practice/${taskId}`);
    return response.data;
  },

  updateTaskProgress: async (taskId: string, lastPlayedChunkIndex: number) => {
    const response = await axios.post<{ message: string }>(
      `${API_URL}/tasks/${taskId}/progress`,
      null,
      {
        params: { last_played_chunk_index: lastPlayedChunkIndex },
      }
    );
    return response.data;
  },

  downloadSrtUrl: (taskId: string) => `${API_URL}/download/${taskId}/srt`,

  getTasks: async () => {
    const response = await axios.get<Task[]>(`${API_URL}/tasks`);
    return response.data;
  },
};

export interface Config {
  asr: {
    method: string;
    parakeet_model_dir: string;
    enable_demucs: boolean;
    enable_vad: boolean;
  };
  llm: {
    api_key?: string;
    base_url?: string;
    model?: string;
  };
  tts: {
    api_key?: string;
    model?: string;
    defaults: {
      language: string;
      speed: string;
      tone: string;
    };
    voice_map: {
      male: string;
      female: string;
    };
  };
  app: {
    max_split_length: number;
    use_llm: boolean;
    source_language: string;
    target_language: string;
    spacy_model_map: Record<string, string>;
  };
}


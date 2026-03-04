import { useState, useEffect, useRef } from 'react'
import { FileText, Upload, CheckCircle2, AlertCircle, Trash2 } from 'lucide-react'
import { api } from '../../../api'

export default function StepCvUpload({ onComplete }: { onComplete: () => void }) {
  const [cvs, setCvs] = useState<any[]>([])
  const [cvFile, setCvFile] = useState<File | null>(null)
  const [cvLabel, setCvLabel] = useState('')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const onCompleteRef = useRef(onComplete)
  onCompleteRef.current = onComplete

  useEffect(() => {
    api.listCVs().then((res: any) => {
      const list = Array.isArray(res) ? res : []
      setCvs(list)
      setLoaded(true)
      if (list.length > 0) onCompleteRef.current()
    }).catch(() => setLoaded(true))
  }, [])

  const handleFile = (file: File) => {
    if (!/\.(pdf|doc|docx)$/i.test(file.name)) {
      setError('Please upload a PDF, DOC, or DOCX file')
      return
    }
    setCvFile(file)
    setCvLabel(file.name.replace(/\.[^.]+$/, ''))
    setError(null)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const handleUpload = async () => {
    if (!cvFile) return
    setUploading(true)
    setError(null)
    try {
      const label = cvLabel.trim() || cvFile.name.replace(/\.[^.]+$/, '')
      const res = await api.uploadCV(cvFile, label)
      if (res && !res.error) {
        setCvs((prev) => [res, ...prev])
        setCvFile(null)
        setCvLabel('')
        onComplete()
      } else {
        setError(res?.error || 'Upload failed')
      }
    } catch (e: any) {
      setError(e.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (id: number) => {
    await api.deleteCV(id)
    setCvs((prev) => prev.filter((c) => c.id !== id))
  }

  if (!loaded) return (
    <div className="flex items-center justify-center min-h-full">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
    </div>
  )

  return (
    <div className="p-4 sm:p-6 md:p-8 max-w-xl mx-auto">
      <div className="fadeIn" style={{ animationDelay: '0ms', opacity: 0 }}>
        <div className="flex items-center gap-3 mb-6">
          <div className="rounded-xl bg-amber-500/10 p-2 border border-amber-500/20">
            <FileText className="h-5 w-5 text-amber-500" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Upload Your CV</h2>
            <p className="text-xs text-white/40">The bot attaches this to every application</p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] p-6 sm:p-8 shadow-2xl fadeIn" style={{ animationDelay: '100ms', opacity: 0 }}>
        {/* Existing CVs */}
        {cvs.length > 0 && (
          <div className="mb-6 space-y-3">
            <span className="block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">Your CVs</span>
            {cvs.map((cv) => (
              <div key={cv.id} className="group flex items-center justify-between rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3 transition-colors">
                <div className="flex items-center gap-3 overflow-hidden">
                  <div className="rounded-lg bg-emerald-500/10 p-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold text-white/80">{cv.label}</p>
                    <p className="truncate text-[10px] text-white/40">{cv.filename}</p>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(cv.id)}
                  className="rounded-lg p-2 text-white/20 opacity-0 transition-all hover:bg-red-500/10 hover:text-red-400 group-hover:opacity-100"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
          className={`relative cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-all ${
            dragOver
              ? 'border-amber-500 bg-amber-500/10'
              : cvFile
                ? 'border-emerald-500/50 bg-emerald-500/5'
                : 'border-white/20 bg-white/[0.02] hover:border-amber-500/50 hover:bg-amber-500/5'
          }`}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.doc,.docx"
            className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
          />
          {cvFile ? (
            <>
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                <FileText className="h-6 w-6 text-emerald-400" />
              </div>
              <p className="text-sm font-bold text-white">{cvFile.name}</p>
              <p className="mt-1 text-xs text-white/40">{(cvFile.size / 1024).toFixed(0)} KB</p>
            </>
          ) : (
            <>
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-white/5 border border-white/10">
                <Upload className="h-6 w-6 text-white/30" />
              </div>
              <p className="text-sm font-bold text-white/60">Drop your CV here</p>
              <p className="mt-1 text-xs text-white/30">or click to browse — PDF, DOC, DOCX</p>
            </>
          )}
        </div>

        {/* Label input */}
        {cvFile && (
          <div className="mt-4">
            <label className="mb-2 block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">Label</label>
            <input
              value={cvLabel}
              onChange={(e) => setCvLabel(e.target.value)}
              placeholder="e.g. My Main CV"
              className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50"
            />
          </div>
        )}

        {error && (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        {/* Upload button */}
        {cvFile && (
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-amber-500 px-6 py-3.5 text-sm font-black uppercase tracking-wider text-black transition-all hover:bg-amber-400 active:scale-[0.98] disabled:opacity-50"
          >
            {uploading ? (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-black border-t-transparent" />
            ) : (
              <><Upload className="h-4 w-4" /> Upload CV</>
            )}
          </button>
        )}
      </div>
    </div>
  )
}

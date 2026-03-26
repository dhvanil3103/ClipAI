import { useState } from 'react';

export default function Home({ onGenerate }) {
  const [url, setUrl] = useState('');
  const [numClips, setNumClips] = useState(3);
  const [duration, setDuration] = useState(60);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (url.trim()) {
      onGenerate({ url, numClips, duration });
    }
  };

  return (
    <main className="min-h-screen relative flex flex-col items-center justify-center px-6 py-24 overflow-x-hidden">
      {/* Ambient background accents */}
      <div className="absolute top-[-10%] left-[20%] w-[500px] h-[500px] bg-primary/10 rounded-full blur-[120px] -z-10 pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[10%] w-[600px] h-[600px] bg-secondary/10 rounded-full blur-[140px] -z-10 pointer-events-none" />

      {/* Hero Section */}
      <section className="max-w-4xl w-full text-center mb-16 space-y-6">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-surface-container-high border border-outline-variant/20 text-xs font-label font-semibold text-primary mb-4">
          <span className="material-symbols-outlined text-[14px]">auto_awesome</span>
          AI-POWERED VIRALITY ENGINE
        </div>
        <div className="font-headline text-6xl md:text-8xl font-bold tracking-tighter leading-none text-transparent bg-clip-text bg-gradient-to-r from-primary to-secondary drop-shadow-[0_0_30px_rgba(202,152,255,0.3)]">
          ClipAI
        </div>
        <h1 className="font-headline text-5xl md:text-7xl font-bold tracking-tighter leading-[1.1]">
          Turn Podcasts into <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-secondary drop-shadow-[0_0_15px_rgba(202,152,255,0.4)]">
            Viral Clips
          </span>
        </h1>
        <p className="font-body text-on-surface-variant text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
          Our AI Digital Curator scans your long-form content, identifies the most engaging hooks,
          and reformats them for 9:16 social success.
        </p>
      </section>

      {/* Input Container */}
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-3xl glass-panel bg-surface-bright/40 rounded-xl p-8 md:p-12 shadow-[0_0_40px_-10px_rgba(0,0,0,0.5)]"
      >
        <div className="space-y-10">
          {/* URL Input */}
          <div className="space-y-3">
            <label className="font-label text-xs font-bold uppercase tracking-widest text-on-surface-variant/80 ml-1">
              Podcast Source URL
            </label>
            <div className="relative group">
              <div className="absolute inset-y-0 left-5 flex items-center pointer-events-none text-primary">
                <span className="material-symbols-outlined">link</span>
              </div>
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="w-full bg-surface-container-lowest border-none ring-1 ring-outline-variant/30 focus:ring-2 focus:ring-primary/50 rounded-lg py-5 pl-14 pr-6 text-on-surface font-body transition-all placeholder:text-outline/50 text-lg outline-none"
                placeholder="https://youtube.com/watch?v=..."
              />
            </div>
          </div>

          {/* Controls Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Number of Clips */}
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <label className="font-label text-xs font-bold uppercase tracking-widest text-on-surface-variant/80 ml-1">
                  Number of Clips
                </label>
                <span className="text-primary font-headline font-bold">
                  {String(numClips).padStart(2, '0')}
                </span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                value={numClips}
                onChange={(e) => setNumClips(Number(e.target.value))}
                className="w-full h-1.5 bg-surface-container-high rounded-full appearance-none cursor-pointer accent-[#ca98ff]"
              />
              <div className="flex justify-between text-[10px] text-outline font-label uppercase">
                <span>1 clip</span>
                <span>10 clips</span>
              </div>
            </div>

            {/* Target Duration */}
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <label className="font-label text-xs font-bold uppercase tracking-widest text-on-surface-variant/80 ml-1">
                  Target Duration
                </label>
                <span className="text-secondary font-headline font-bold">{duration}s</span>
              </div>
              <input
                type="range"
                min="15"
                max="180"
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
                className="w-full h-1.5 bg-surface-container-high rounded-full appearance-none cursor-pointer accent-[#ff51fa]"
              />
              <div className="flex justify-between text-[10px] text-outline font-label uppercase">
                <span>15s</span>
                <span>180s</span>
              </div>
            </div>
          </div>

          {/* CTA */}
          <div className="pt-4">
            <button
              type="submit"
              className="w-full group relative flex items-center justify-center gap-3 py-6 bg-gradient-primary rounded-lg text-on-primary-fixed font-headline font-bold text-xl tracking-tight shadow-[0_0_30px_-5px_rgba(202,152,255,0.4)] hover:shadow-[0_0_50px_-5px_rgba(202,152,255,0.6)] transition-all active:scale-[0.98]"
            >
              <span className="material-symbols-outlined group-hover:rotate-12 transition-transform">bolt</span>
              Generate Viral Clips
              <div className="absolute inset-0 rounded-lg border-2 border-white/20 opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
            <p className="text-center mt-4 text-[10px] text-outline font-label uppercase tracking-widest">
              ESTIMATED PROCESSING TIME:{' '}
              <span className="text-on-surface-variant font-bold">~2 MINUTES</span>
            </p>
          </div>
        </div>
      </form>

      {/* Feature Cards */}
      <div className="mt-20 w-full max-w-6xl grid grid-cols-1 md:grid-cols-3 gap-6 mb-20">
        <div className="p-6 rounded-2xl bg-surface-container-low/40 border border-outline-variant/10 flex items-start gap-4">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary shrink-0">
            <span className="material-symbols-outlined">trending_up</span>
          </div>
          <div>
            <h4 className="font-headline font-bold text-sm mb-1">Virality Scoring</h4>
            <p className="text-xs text-on-surface-variant font-body leading-relaxed">
              AI predicts which moments have the highest potential for TikTok and Reels growth.
            </p>
          </div>
        </div>
        <div className="p-6 rounded-2xl bg-surface-container-low/40 border border-outline-variant/10 flex items-start gap-4">
          <div className="w-10 h-10 rounded-full bg-secondary/10 flex items-center justify-center text-secondary shrink-0">
            <span className="material-symbols-outlined">closed_caption</span>
          </div>
          <div>
            <h4 className="font-headline font-bold text-sm mb-1">Smart Captions</h4>
            <p className="text-xs text-on-surface-variant font-body leading-relaxed">
              Dynamic, animated captions generated automatically with 99% accuracy.
            </p>
          </div>
        </div>
        <div className="p-6 rounded-2xl bg-surface-container-low/40 border border-outline-variant/10 flex items-start gap-4">
          <div className="w-10 h-10 rounded-full bg-tertiary-dim/10 flex items-center justify-center text-tertiary-dim shrink-0">
            <span className="material-symbols-outlined">aspect_ratio</span>
          </div>
          <div>
            <h4 className="font-headline font-bold text-sm mb-1">Auto-Reframing</h4>
            <p className="text-xs text-on-surface-variant font-body leading-relaxed">
              Intelligent subject tracking keeps the speaker perfectly centered in vertical frame.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}

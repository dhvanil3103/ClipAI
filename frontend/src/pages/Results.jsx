import { useState } from 'react';

export default function Results({ clips, onNewClip }) {
  const [activeVideo, setActiveVideo] = useState(null);

  const cardData = clips && clips.length > 0
    ? clips
    : [
        {
          title: 'The Truth About AI Productivity',
          duration: '58s',
          score: 98,
          scoreColor: 'tertiary',
          tag: 'VIRAL POTENTIAL',
          tagColor: 'secondary',
          thumbnail: null,
          videoPath: null,
        },
        {
          title: 'Why Remote Work is actually failing',
          duration: '42s',
          score: 92,
          scoreColor: 'secondary',
          tag: 'TRENDING TOPIC',
          tagColor: 'primary',
          thumbnail: null,
          videoPath: null,
        },
        {
          title: 'The secret to 4-hour work weeks',
          duration: '1:15',
          score: 95,
          scoreColor: 'tertiary',
          tag: 'HOOK OPTIMIZED',
          tagColor: 'tertiary',
          thumbnail: null,
          videoPath: null,
        },
      ];

  const scoreStyle = (color) => {
    if (color === 'secondary') return { dot: 'bg-secondary shadow-[0_0_8px_#ff51fa]', text: 'text-secondary' };
    return { dot: 'bg-tertiary shadow-[0_0_8px_#48e4da]', text: 'text-tertiary' };
  };

  const tagStyle = (color) => {
    if (color === 'secondary') return 'bg-secondary/10 text-secondary border-secondary/20';
    if (color === 'tertiary') return 'bg-tertiary/10 text-tertiary border-tertiary/20';
    return 'bg-primary/10 text-primary border-primary/20';
  };

  return (
    <main className="pt-12 pb-12 px-6 md:px-12 min-h-screen">
      {/* Header */}
      <header className="mb-12 pt-8 space-y-2">
        <nav className="flex items-center gap-2 text-on-surface-variant text-xs font-label uppercase tracking-widest">
          <button onClick={onNewClip} className="hover:text-primary transition-colors">
            Home
          </button>
          <span className="material-symbols-outlined text-[10px]">chevron_right</span>
          <span className="text-primary">Results</span>
        </nav>
        <h1 className="text-4xl md:text-5xl font-headline font-extrabold tracking-tighter text-on-surface">
          Generation{' '}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-secondary">
            Complete
          </span>
        </h1>
        <p className="text-on-surface-variant max-w-xl font-body text-sm leading-relaxed">
          Our AI has identified the most viral-ready moments from your long-form content. These
          9:16 clips are optimized for TikTok, Reels, and Shorts.
        </p>
      </header>

      {/* Results Grid */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
        {cardData.map((clip, i) => {
          const score = scoreStyle(clip.scoreColor);
          return (
            <div
              key={i}
              onClick={() => clip.videoPath && setActiveVideo(clip)}
              className={`group relative aspect-[9/16] rounded-xl overflow-hidden bg-surface-container-highest transition-all duration-500 hover:-translate-y-2 shadow-xl hover:shadow-[0_20px_40px_-15px_rgba(202,152,255,0.2)] ${clip.videoPath ? 'cursor-pointer' : 'cursor-default'}`}
            >
              {/* Background */}
              <div className="absolute inset-0 z-0">
                {clip.thumbnail ? (
                  <img
                    src={clip.thumbnail}
                    alt={clip.title}
                    className="w-full h-full object-cover grayscale-[0.2] group-hover:scale-110 transition-transform duration-700"
                  />
                ) : (
                  <div className="w-full h-full bg-gradient-to-tr from-surface-container-lowest via-surface-container to-surface-container-highest" />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-background via-background/20 to-transparent" />
              </div>

              {/* Engagement Score Badge */}
              <div className="absolute top-6 left-6 z-10">
                <div className="glass-panel bg-surface-container-highest/60 px-3 py-1.5 rounded-full border border-white/10 flex items-center gap-2 shadow-lg">
                  <span className={`flex h-2 w-2 rounded-full ${score.dot}`} />
                  <span className="font-label text-xs font-bold tracking-tight">
                    Engagement Score:{' '}
                    <span className={score.text}>{clip.score}</span>
                  </span>
                </div>
              </div>

              {/* Hover Play — only shown when video is available */}
              {clip.videoPath && (
                <div className="absolute inset-0 flex items-center justify-center z-20 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                  <div className="w-16 h-16 rounded-full bg-primary/20 backdrop-blur-md flex items-center justify-center border border-primary/40 shadow-[0_0_30px_rgba(202,152,255,0.4)]">
                    <span
                      className="material-symbols-outlined text-primary text-4xl"
                      style={{ fontVariationSettings: "'FILL' 1" }}
                    >
                      play_arrow
                    </span>
                  </div>
                </div>
              )}

              {/* Bottom Metadata */}
              <div className="absolute bottom-0 left-0 right-0 p-6 z-10 space-y-3">
                <div className="flex items-end justify-between gap-4">
                  <div className="flex-1">
                    <h3 className="font-headline font-bold text-lg leading-tight text-on-surface">
                      {clip.title}
                    </h3>
                    <div className="mt-2 flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 rounded border font-label text-[10px] ${tagStyle(clip.tagColor)}`}
                      >
                        {clip.tag}
                      </span>
                    </div>
                  </div>
                  <div className="glass-panel bg-surface-container-low/80 px-3 py-1.5 rounded-lg border border-white/5 font-label text-xs font-medium text-on-surface shrink-0">
                    {clip.duration}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </section>

      {/* Video Player Modal */}
      {activeVideo && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm px-4"
          onClick={() => setActiveVideo(null)}
        >
          <div
            className="relative w-full max-w-sm"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close button */}
            <button
              onClick={() => setActiveVideo(null)}
              className="absolute -top-10 right-0 text-on-surface-variant hover:text-on-surface transition-colors flex items-center gap-1 font-label text-xs uppercase tracking-widest"
            >
              <span className="material-symbols-outlined text-lg">close</span>
              Close
            </button>
            <video
              src={activeVideo.videoPath}
              controls
              autoPlay
              className="w-full rounded-xl shadow-[0_0_60px_-10px_rgba(202,152,255,0.4)]"
              style={{ aspectRatio: '9/16', background: '#000' }}
            />
            <p className="mt-3 text-center font-headline font-semibold text-on-surface text-sm">
              {activeVideo.title}
            </p>
          </div>
        </div>
      )}

      {/* New Clip FAB (mobile) */}
      <button
        onClick={onNewClip}
        className="md:hidden fixed bottom-6 right-6 w-14 h-14 rounded-full bg-gradient-primary text-on-primary-fixed shadow-2xl flex items-center justify-center z-40"
      >
        <span className="material-symbols-outlined">auto_awesome</span>
      </button>
    </main>
  );
}

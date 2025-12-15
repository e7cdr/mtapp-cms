    document.addEventListener('DOMContentLoaded', function () {
    // Thumbnail swiper (bottom)
    var collageSwiper2 = new Swiper('.collage-swiper2-container', {
        slidesPerView: "auto",
        allowTouchMove: false,
        watchSlidesProgress: true,
    });

    // Main swiper (big one with fade)
    const totalSlides = document.querySelectorAll('.collage-swiper1-container .swiper-slide').length;

    var collageSwiper1 = new Swiper('.collage-swiper1-container', {
        loop: totalSlides > 2,
        navigation: {
            nextEl: ".swiper-button-next",
            prevEl: ".swiper-button-prev",
        },
        thumbs: { swiper: collageSwiper2 },
        effect: 'fade',
        fadeEffect: { crossFade: true },
        speed: 500,
        keyboard: { enabled: true },
        allowTouchMove: true,
        autoplay: {
            delay: 2000,
            pauseOnMouseEnter: true,
        },
    });

    // Store YouTube players by real index (works with loop)
    const players = {};

    // Load and play a YouTube video inside a placeholder div
function loadAndPlayYouTubeVideo(container) {
    const videoId = container.dataset.videoId;
    const player = new YT.Player(container, {
        width: '100%',
        height: '100%',
        videoId: videoId,
        playerVars: {
            autoplay: 1,
            rel: 0,
            modestbranding: 1,
            playsinline: 1,
            fs: 1,
            enablejsapi: 1,
            origin: window.location.origin  // Fixes postMessage errors on localhost
        },
        events: {
            onReady: (e) => {
                const iframe = e.target.getIframe();
                iframe.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share; passive-touch');
                iframe.setAttribute('loading', 'lazy');
                e.target.playVideo();
            }
        }
    });
    return player;
}

    // === MAIN LOGIC: Play video only on active slide + auto-advance when finished ===
    collageSwiper1.on('slideChange', function () {
        const prevRealIndex = this.previousRealIndex !== undefined ? this.previousRealIndex : this.realIndex;
        const activeRealIndex = this.realIndex;

        // 1. Pause & clean up previous video
        if (players[prevRealIndex]) {
            players[prevRealIndex].pauseVideo();
            // Remove old "ended" listener to prevent duplicates
            if (players[prevRealIndex]._onEnded) {
                players[prevRealIndex].removeEventListener('onStateChange', players[prevRealIndex]._onEnded);
                delete players[prevRealIndex]._onEnded;
            }
        }

        // 2. Get current slide
        const activeSlide = this.slides[this.activeIndex];
        const youtubeContainer = activeSlide.querySelector('.youtube-lazy');

        if (youtubeContainer) {
            // --- It's a YouTube slide ---
            if (!players[activeRealIndex]) {
                // First time → create player
                players[activeRealIndex] = loadAndPlayYouTubeVideo(youtubeContainer);
            } else {
                // Already created → just play
                players[activeRealIndex].playVideo();
            }

            // When this video ends → go to next slide
            const player = players[activeRealIndex];
            const onVideoEnded = (event) => {
                if (event.data === YT.PlayerState.ENDED) {
                    collageSwiper1.slideNext();
                }
            };
            player._onEnded = onVideoEnded;
            player.addEventListener('onStateChange', onVideoEnded);

        } else {
            // --- It's an image slide → auto-advance after delay ---
            setTimeout(() => {
                // Only advance if we're still on the same slide
                if (collageSwiper1.realIndex === activeRealIndex) {
                    collageSwiper1.slideNext();
                }
            }, 6000); // 6 seconds for images — change as you like
        }
    });

    // === Load first video immediately if the first slide is YouTube ===
    collageSwiper1.on('init', function () {
        setTimeout(() => {
            const firstSlide = this.slides[this.activeIndex];
            const ytContainer = firstSlide.querySelector('.youtube-lazy');
            if (ytContainer) {
                this.emit('slideChange'); // triggers the full logic above
            }
        }, 300);
    });

    // Trigger init manually (sometimes needed when loop: true)
    collageSwiper1.init();

    // === Load YouTube Iframe API ===
    const tag = document.createElement('script');
    tag.src = "https://www.youtube.com/iframe_api";
    const firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
});
document.addEventListener('DOMContentLoaded', function () {
    // Thumbnail swiper (bottom)
    var collageSwiper2 = new Swiper('.collage-swiper2-container', {
        slidesPerView: "auto",
        allowTouchMove: false,
        watchSlidesProgress: true,
    });

    // Main swiper — no built-in autoplay
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
        on: {
            init: function () {
                const firstSlide = this.slides[this.activeIndex];
                const youtubeContainer = firstSlide.querySelector('.youtube-lazy');

                if (youtubeContainer) {
                    // Small delay only for first YouTube slide to avoid race conditions
                    setTimeout(() => handleActiveSlide.call(this), 300);
                } else {
                    handleActiveSlide.call(this);
                }
            },
            slideChange: function () {
                handleActiveSlide.call(this);
            }
        }
    });

    // Store YouTube players by realIndex
    const players = {};

    // Create and play a YouTube player
    function loadAndPlayYouTubeVideo(container) {
        const videoId = container.dataset.videoId;
        const player = new YT.Player(container, {
            width: '100%',
            height: '100%',
            videoId: videoId,
            playerVars: {
                autoplay: 1,
                mute: 1,                // ← Critical: allows true autoplay without click
                rel: 0,
                modestbranding: 1,
                playsinline: 1,
                fs: 1,
                enablejsapi: 1,
                origin: window.location.origin
            },
            events: {
                onReady: function (e) {
                    const iframe = e.target.getIframe();
                    iframe.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share');
                    iframe.setAttribute('loading', 'lazy');

                    e.target.mute();        // Extra safety mute
                    e.target.playVideo();   // Ensures playback starts
                }
            }
        });
        return player;
    }

    // Core logic: handle current active slide
    function handleActiveSlide() {
        const activeRealIndex = this.realIndex;
        const activeSlide = this.slides[this.activeIndex];
        const youtubeContainer = activeSlide.querySelector('.youtube-lazy');

        // Clean up previous video (if any)
        if (this.previousIndex !== undefined && this.previousIndex !== this.activeIndex) {
            const prevPlayer = players[activeRealIndex]; // fallback, not critical
            if (prevPlayer) {
                prevPlayer.pauseVideo();
                if (prevPlayer._onEnded) {
                    prevPlayer.removeEventListener('onStateChange', prevPlayer._onEnded);
                    delete prevPlayer._onEnded;
                }
            }
        }

        if (youtubeContainer) {
            // YouTube slide
            let player = players[activeRealIndex];

            if (!player) {
                player = players[activeRealIndex] = loadAndPlayYouTubeVideo(youtubeContainer);
            } else {
                player.playVideo();
            }

            // Auto-advance when video ends
            const onVideoEnded = function (event) {
                if (event.data === YT.PlayerState.ENDED) {
                    collageSwiper1.slideNext();
                }
            };

            if (!player._onEnded) {
                player._onEnded = onVideoEnded;
                player.addEventListener('onStateChange', onVideoEnded);
            }

        } else {
            // Image slide
            setTimeout(() => {
                if (collageSwiper1.realIndex === activeRealIndex) {
                    collageSwiper1.slideNext();
                }
            }, 6000); // Adjust image duration here
        }
    }

    // Load YouTube Iframe API
    const tag = document.createElement('script');
    tag.src = "https://www.youtube.com/iframe_api";
    const firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
});
document.addEventListener('DOMContentLoaded', function () {
    // Thumbnail swiper (bottom)
    var collageSwiper2 = new Swiper('.collage-swiper2-container', {
        slidesPerView: "auto",
        allowTouchMove: false,
        watchSlidesProgress: true,
    });

    // Main swiper
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
                    // Small delay to give YouTube API time to load
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

    // Track user interaction for unmuting
    let userHasInteracted = false;
    document.addEventListener('click', () => { userHasInteracted = true; }, { once: true });
    document.addEventListener('touchstart', () => { userHasInteracted = true; }, { once: true });
    document.addEventListener('keydown', () => { userHasInteracted = true; }, { once: true });

    // Direct player creation (no queue)
    function loadAndPlayYouTubeVideo(container) {
        // Safety guard: if API not ready yet, do nothing — callback will retry
        if (typeof YT === 'undefined' || !YT.Player) {
            console.log('YT not ready yet — will retry via onYouTubeIframeAPIReady');
            return null;
        }

        const videoId = container.dataset.videoId;

        const player = new YT.Player(container, {
            width: '100%',
            height: '100%',
            videoId: videoId,
            playerVars: {
                autoplay: 1,
                mute: 1,
                rel: 0,
                modestbranding: 1,
                playsinline: 1,
                fs: 1,
                enablejsapi: 1,
            },
            events: {
                onReady: (e) => {
                    const iframe = e.target.getIframe();
                    iframe.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share');
                    iframe.setAttribute('loading', 'lazy');

                    e.target.playVideo();

                    if (userHasInteracted) {
                        e.target.unMute();
                        e.target.setVolume(10);
                    }
                },
                onStateChange: (e) => {
                    if (userHasInteracted && e.data !== YT.PlayerState.ENDED) {
                        e.target.unMute();
                        e.target.setVolume(10);
                    }
                }
            }
        });

        return player;
    }

    // Core slide handling
    function handleActiveSlide() {
        const activeRealIndex = this.realIndex;
        const activeSlide = this.slides[this.activeIndex];
        const youtubeContainer = activeSlide.querySelector('.youtube-lazy');

        // Clean up previous video (only when a real previous slide exists)
        if (this.previousRealIndex !== undefined && this.previousRealIndex !== activeRealIndex) {
            const prevPlayer = players[this.previousRealIndex];
            if (prevPlayer) {
                prevPlayer.pauseVideo();
                if (prevPlayer._onEnded) {
                    prevPlayer.removeEventListener('onStateChange', prevPlayer._onEnded);
                    delete prevPlayer._onEnded;
                }
            }
        }

        if (youtubeContainer) {
            let player = players[activeRealIndex];

            if (!player) {
                player = players[activeRealIndex] = loadAndPlayYouTubeVideo(youtubeContainer);
            } else {
                player.playVideo();

                if (userHasInteracted) {
                    player.unMute();
                    player.setVolume(10);
                }
            }

            // Auto-advance when video ends
            const onVideoEnded = (event) => {
                if (event.data === YT.PlayerState.ENDED) {
                    collageSwiper1.slideNext();
                }
            };

            // Prevent duplicate listeners
            if (!player._onEnded) {
                player._onEnded = onVideoEnded;
                player.addEventListener('onStateChange', onVideoEnded);
            }

        } else {
            // Image slide → auto-advance after 6 seconds
            setTimeout(() => {
                if (collageSwiper1.realIndex === activeRealIndex) {
                    collageSwiper1.slideNext();
                }
            }, 6000);
        }
    }

    // Load YouTube Iframe API (only once)
    if (!window.YT) {
        const tag = document.createElement('script');
        tag.src = "https://www.youtube.com/iframe_api";
        const firstScriptTag = document.getElementsByTagName('script')[0];
        firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

            // Robust safety net: ensure first YouTube slide plays even if API loads late
           window.onYouTubeIframeAPIReady = function () {
            console.log('YouTube IFrame API ready');

            // Retry current active slide if it's YouTube and has no player yet
            const activeSlide = collageSwiper1.slides[collageSwiper1.activeIndex];
            const youtubeContainer = activeSlide.querySelector('.youtube-lazy');

            if (youtubeContainer && !players[collageSwiper1.realIndex]) {
                console.log('Retrying active YouTube slide due to late API load');
                setTimeout(() => handleActiveSlide.call(collageSwiper1), 100);
            }
        };
    }
});
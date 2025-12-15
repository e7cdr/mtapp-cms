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

    // Store YouTube players by realIndex + track if user has interacted
    const players = {};
    let userHasInteracted = false;

    // Detect any user interaction (click, touch, key) once
    document.addEventListener('click', () => { userHasInteracted = true; }, { once: true });
    document.addEventListener('touchstart', () => { userHasInteracted = true; }, { once: true });
    document.addEventListener('keydown', () => { userHasInteracted = true; }, { once: true });

    // Create YouTube player (starts muted for reliable autoplay)
    function loadAndPlayYouTubeVideo(container) {
        const videoId = container.dataset.videoId;
        const player = new YT.Player(container, {
            width: '100%',
            height: '100%',
            videoId: videoId,
            playerVars: {
                autoplay: 1,
                mute: 1,                  // Start muted → guaranteed autoplay
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

                    e.target.playVideo();

                    // If user already interacted before ready, unmute immediately
                    if (userHasInteracted) {
                        e.target.unMute();
                        e.target.setVolume(100); // or your preferred level, e.g. 50
                    }
                },
                onStateChange: function (e) {
                    // Unmute on any state change if user has interacted
                    if (userHasInteracted && e.data !== YT.PlayerState.ENDED) {
                        e.target.unMute();
                        e.target.setVolume(100);
                    }
                }
            }
        });
        return player;
    }

    // Core logic
    function handleActiveSlide() {
        const activeRealIndex = this.realIndex;
        const activeSlide = this.slides[this.activeIndex];
        const youtubeContainer = activeSlide.querySelector('.youtube-lazy');

        // Clean up previous video
        if (this.previousIndex !== undefined && this.previousIndex !== this.activeIndex) {
            const prevPlayer = players[activeRealIndex];
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

                // Unmute if user has interacted
                if (userHasInteracted) {
                    player.unMute();
                    player.setVolume(100);
                }
            }

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
            }, 6000);
        }
    }

    // Load YouTube Iframe API
    const tag = document.createElement('script');
    tag.src = "https://www.youtube.com/iframe_api";
    const firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
});
document.addEventListener('DOMContentLoaded', function () {
    // Thumbnails swiper (bottom)
    var thumbSwiper2 = new Swiper('.thumb-swiper2-container', {
        slidesPerView: 'auto',
        spaceBetween: 10,
        freeMode: true,
        watchSlidesProgress: true,
        breakpoints: {
            750: {
                slidesPerView: 3,
                spaceBetween: 20,
            }
        }
    });

    // Count slides to fix loop warning
    const totalSlides = document.querySelectorAll('.thumb-swiper1-container .swiper-slide').length;

    // Main fade swiper (top)
    var thumbSwiper1 = new Swiper('.thumb-swiper1-container', {
        spaceBetween: 10,
        loop: totalSlides > 2,                    // Auto-disable loop if ≤2 slides
        navigation: {
            nextEl: ".swiper-button-next",
            prevEl: ".swiper-button-prev",
        },
        thumbs: {
            swiper: thumbSwiper2,
        },
        effect: 'fade',
        fadeEffect: {
            crossFade: true
        },
        speed: 500,
        keyboard: { enabled: true },
        autoplay: false,                          // We control timing manually now
        allowTouchMove: true
    });

    const players = {};

    let youtubeAPIReady = false;
    let pendingPlayers = [];

    // Global callback required by YouTube API
    window.onYouTubeIframeAPIReady = function () {
        youtubeAPIReady = true;

        // Process any players that were requested before API was ready
        pendingPlayers.forEach(({ container, index }) => {
            players[index] = createYouTubePlayer(container, index);
        });
        pendingPlayers = [];
    };

    function createYouTubePlayer(container, index) {
        const videoId = container.dataset.videoId;

        const player = new YT.Player(container, {
            width: '100%',
            height: '100%',
            videoId: videoId,
            playerVars: {
                autoplay: 1,
                mute: 1,                  // Explicitly mute for reliable autoplay
                rel: 0,
                modestbranding: 1,
                playsinline: 1,
                fs: 1,
                enablejsapi: 1,
                origin: window.location.origin
            },
            events: {
                onReady: (e) => {
                    const iframe = e.target.getIframe();
                    iframe.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share');
                    iframe.setAttribute('loading', 'lazy');
                    e.target.mute();       // Ensure muted
                    e.target.playVideo();
                }
            }
        });

        return player;
    }

    function loadAndPlayYouTubeVideo(container, slideIndex) {
        if (youtubeAPIReady) {
            players[slideIndex] = createYouTubePlayer(container, slideIndex);
        } else {
            // Queue until API is ready
            pendingPlayers.push({ container, index: slideIndex });
        }
    }

    // Main magic — runs every time the main slide changes
    thumbSwiper1.on('slideChange transitionEnd', function () {
        const prevIndex = this.previousRealIndex !== undefined ? this.previousRealIndex : this.realIndex;
        const activeIndex = this.realIndex;

        // Pause & clean previous video
        if (players[prevIndex]) {
            players[prevIndex].pauseVideo();
            if (players[prevIndex]._onEnded) {
                players[prevIndex].removeEventListener('onStateChange', players[prevIndex]._onEnded);
            }
        }

        const activeSlide = this.slides[this.activeIndex];
        const youtubeContainer = activeSlide.querySelector('.youtube-lazy');

            if (youtubeContainer) {
                if (!players[activeIndex]) {
                    loadAndPlayYouTubeVideo(youtubeContainer, activeIndex);  // Pass index
                } else {
                    players[activeIndex].playVideo();
                }

            // Auto-advance when video ends
            const player = players[activeIndex];
            const onVideoEnded = (event) => {
                if (event.data === YT.PlayerState.ENDED) {
                    thumbSwiper1.slideNext();
                }
            };
            player._onEnded = onVideoEnded;
            player.addEventListener('onStateChange', onVideoEnded);

        } else {
            // Image slide → auto-advance after 6 seconds
            setTimeout(() => {
                if (thumbSwiper1.realIndex === activeIndex) {
                    thumbSwiper1.slideNext();
                }
            }, 6000);
        }
    });

    // Start everything on init
    thumbSwiper1.on('init', function () {
        setTimeout(() => this.emit('slideChange'), 400);
    });
    thumbSwiper1.init();

    // Load YouTube API only once per page
    if (!window.YT) {
        const tag = document.createElement('script');
        tag.src = "https://www.youtube.com/iframe_api";
        const firstScript = document.getElementsByTagName('script')[0];
        firstScript.parentNode.insertBefore(tag, firstScript);
    }
});
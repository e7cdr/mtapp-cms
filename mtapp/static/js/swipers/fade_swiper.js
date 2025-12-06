
document.addEventListener('DOMContentLoaded', () => {
    const fadeContainer = document.querySelector('.fade-swiper-container');
    if (!fadeContainer) return;

    const totalSlides = fadeContainer.querySelectorAll('.swiper-slide').length;

    // === 1. SWIPER + YOUTUBE LOGIC ===
    const players = {};

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
                origin: window.location.origin
            },
            events: {
                onReady: (e) => {
                    const iframe = e.target.getIframe();
                    iframe.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share');
                    iframe.setAttribute('loading', 'lazy');
                    e.target.playVideo();
                }
            }
        });
        return player;
    }

    const fadeSwiper = new Swiper(fadeContainer, {
        slidesPerView: 1,
        spaceBetween: 0,
        loop: totalSlides > 2,
        pagination: { el: '.swiper-pagination' },
        effect: 'fade',
        fadeEffect: { crossFade: true },
        autoplay: false,
        speed: 2000,
        lazy: true,
        keyboard: true,
        grabCursor: true,
        allowTouchMove: true
    });

    fadeSwiper.on('slideChange transitionEnd', function () {
        const prevIndex = this.previousRealIndex !== undefined ? this.previousRealIndex : this.realIndex;
        const activeIndex = this.realIndex;

        // Stop previous video
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
                players[activeIndex] = loadAndPlayYouTubeVideo(youtubeContainer);
            } else {
                players[activeIndex].playVideo();
            }

            const player = players[activeIndex];
            const onEnded = (event) => {
                if (event.data === YT.PlayerState.ENDED) {
                    fadeSwiper.slideNext();
                }
            };
            player._onEnded = onEnded;
            player.addEventListener('onStateChange', onEnded);
        } else {
            // Image slide → auto-advance after 6 seconds
            setTimeout(() => {
                if (fadeSwiper.realIndex === activeIndex) {
                    fadeSwiper.slideNext();
                }
            }, 6000);
        }
    });

    // Kickstart first slide
    fadeSwiper.on('init', function () {
        setTimeout(() => this.emit('slideChange'), 400);
    });
    fadeSwiper.init();

    // Load YouTube API only once
    if (!window.YT) {
        const tag = document.createElement('script');
        tag.src = "https://www.youtube.com/iframe_api";
        const firstScript = document.getElementsByTagName('script')[0];
        firstScript.parentNode.insertBefore(tag, firstScript);
    }

    // === 2. GSAP TITLE ANIMATION (zero forced reflows) ===
    const titleEl = document.querySelector('.fade-title h1');
    const section = document.querySelector('.fade-swiper-section');

    if (titleEl && section) {
        document.fonts.ready.then(() => {
            gsap.registerPlugin(ScrollTrigger, SplitText);

            // THIS LINE KILLS ALL FORCED REFLOWS
            gsap.context(() => {
                const split = new SplitText(titleEl, { type: "chars" });

                const tl = gsap.timeline({
                    scrollTrigger: {
                        trigger: section,
                        start: "top 80%",
                        toggleActions: "play none none reverse"
                    }
                });

                tl.fromTo(fadeContainer,
                    { opacity: 0, y: 60 },
                    { opacity: 1, y: 0, duration: 1.4, ease: "power3.out" }
                );

                tl.to(split.chars, {
                    color: "#ffe66cff",
                    x: -3,
                    scale: 1.01,
                    duration: 0.9,
                    stagger: { from: "random", each: 0.04 },
                    repeat: -1,
                    yoyo: true,
                    repeatDelay: 3,
                    ease: "sine.inOut"
                }, "-=0.8");

            }, section); // ← scoped = no layout thrashing
        });
    }
});
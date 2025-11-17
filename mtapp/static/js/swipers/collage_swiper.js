document.addEventListener('DOMContentLoaded', function(){
    var collageSwiper2 = new Swiper('.collage-swiper2-container', {
        slidesPerView: "auto",  // Fixed 3 columns

        allowTouchMove: false,  // No swiping
        watchSlidesProgress: true,
    });

    var collageSwiper1 = new Swiper('.collage-swiper1-container', {
        loop: true,
        // autoplay: {
        //     waitForTransition: true,
        //     delay: 3000,
        // },
        navigation: {
            nextEl: ".swiper-button-next",
            prevEl: ".swiper-button-prev",
        },
        thumbs: {
            swiper: collageSwiper2,
        },
        effect: 'fade',
        speed: 500,
        keyboard: {
            enabled: true,
        }
    });
});

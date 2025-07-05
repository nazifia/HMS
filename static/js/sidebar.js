(function($) {
    "use strict"; // Start of use strict

    // Function to toggle mobile sidebar
    function toggleMobileSidebar() {
        const sidebar = $('#accordionSidebar'); // Use the ID of the sidebar
        const overlay = $('#sidebar-overlay');
        sidebar.toggleClass('sidebar-open');
        overlay.toggleClass('active');
        $('body').toggleClass('overflow-hidden'); // Prevent scrolling on body when sidebar is open
    }

    // Function to close mobile sidebar
    function closeMobileSidebar() {
        const sidebar = $('#accordionSidebar');
        const overlay = $('#sidebar-overlay');
        sidebar.removeClass('sidebar-open');
        overlay.removeClass('active');
        $('body').removeClass('overflow-hidden');
    }

    // Toggle the side navigation for desktop
    $("#sidebarToggle, #sidebarToggleTop").on('click', function(e) {
        if ($(window).width() >= 768) { // Only for desktop
            $("body").toggleClass("sidebar-toggled");
            $(".sidebar").toggleClass("toggled");
            if ($(".sidebar").hasClass("toggled")) {
                $('.sidebar .collapse').collapse('hide');
            }
        } else { // For mobile
            toggleMobileSidebar();
        }
    });

    // Close mobile sidebar when overlay is clicked
    $('#sidebar-overlay').on('click', function() {
        closeMobileSidebar();
    });

    // Close any open menu accordions when window is resized below 768px
    $(window).resize(function() {
        if ($(window).width() < 768) {
            $('.sidebar .collapse').collapse('hide');
            // Ensure mobile sidebar is closed when resizing from desktop to mobile
            closeMobileSidebar();
        } else {
            // Ensure desktop sidebar is in correct state when resizing from mobile to desktop
            $("body").removeClass("sidebar-toggled");
            $(".sidebar").removeClass("toggled");
        }
    });

    // Prevent the content wrapper from scrolling when the fixed side navigation hovered over
    $('body.fixed-nav .sidebar').on('mousewheel DOMMouseScroll wheel', function(e) {
        if ($(window).width() > 768) {
            var e0 = e.originalEvent,
                delta = e0.wheelDelta || -e0.detail;
            this.scrollTop += (delta < 0 ? 1 : -1) * 30;
            e.preventDefault();
        }
    });

    // Scroll to top button appear
    $(document).on('scroll', function() {
        var scrollDistance = $(this).scrollTop();
        if (scrollDistance > 100) {
            $('.scroll-to-top').fadeIn();
        } else {
            $('.scroll-to-top').fadeOut();
        }
    });

    // Smooth scrolling using jQuery easing
    $(document).on('click', 'a.scroll-to-top', function(e) {
        var $anchor = $(this);
        $('html, body').stop().animate({
            scrollTop: ($($anchor.attr('href')).offset().top)
        }, 1000, 'easeInOutExpo');
        e.preventDefault();
    });

})(jQuery); // End of use strict

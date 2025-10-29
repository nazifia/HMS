(function($) {
    "use strict"; // Start of use strict

    // Function to toggle mobile sidebar
    function toggleMobileSidebar() {
        const sidebar = $('#sidebar-container'); // Use the container ID
        const overlay = $('#sidebar-overlay');
        sidebar.toggleClass('sidebar-open');
        overlay.toggleClass('active');
        $('body').toggleClass('sidebar-open'); // Prevent scrolling on body when sidebar is open
    }

    // Prevent auto-scroll to active menu items on page load
    $(document).ready(function() {
        // Store original scroll position
        const sidebarScrollTop = $('#sidebar-container').scrollTop();
        
        // Prevent Bootstrap's default scroll behavior for accordion
        $('#accordionSidebar .collapse').on('show.bs.collapse', function(e) {
            // Prevent automatic scrolling
            e.stopPropagation();
            return true;
        });
        
        // Maintain manual scroll position
        window.addEventListener('load', function() {
            $('#sidebar-container').scrollTop(0);
        });
        
        // Override any scroll attempts to active elements
        $('.nav-item.active').each(function() {
            $(this).data('original-scroll', false);
        });
    });

    // Function to close mobile sidebar
    function closeMobileSidebar() {
        const sidebar = $('#sidebar-container');
        const overlay = $('#sidebar-overlay');
        sidebar.removeClass('sidebar-open');
        overlay.removeClass('active');
        $('body').removeClass('sidebar-open');
    }

    // Toggle the side navigation for desktop
    $("#sidebarToggle, #sidebarToggleTop").on('click', function(e) {
        e.preventDefault();
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

    // Close mobile sidebar when close button is clicked
    $('#mobileSidebarClose').on('click', function() {
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
            // Also close mobile sidebar when going to desktop
            closeMobileSidebar();
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

    // Prevent automatic scroll to active navigation items
    function preventSidebarAutoScroll() {
        // Override Bootstrap's scroll to active behavior
        if (window.location.hash) {
            // Prevent hash-based scrolling
            window.scrollTo(0, 0);
        }
        
        // Prevent any scroll attempts to active menu items
        const activeElements = document.querySelectorAll('.nav-item.active, .collapse-item.active');
        activeElements.forEach(function(element) {
            // Remove any scrollIntoView calls
            if (element.scrollIntoView) {
                const originalScrollIntoView = element.scrollIntoView;
                element.scrollIntoView = function() {
                    return false;
                };
            }
        });
        
        // Ensure sidebar stays at top or current manual position
        const sidebar = document.getElementById('sidebar-container');
        if (sidebar) {
            sidebar.scrollTop = 0; // Always start at top
        }
    }

    // Apply scroll prevention on page load and navigation
    $(document).ready(function() {
        preventSidebarAutoScroll();
        
        // Prevent scroll on any navigation
        $('.nav-link, .collapse-item').on('click', function(e) {
            // Allow navigation but prevent auto-scroll
            setTimeout(function() {
                preventSidebarAutoScroll();
            }, 100);
        });
        
        // Monitor and prevent any scroll changes in sidebar
        const sidebar = document.getElementById('sidebar-container');
        if (sidebar) {
            let manualScroll = false;
            sidebar.addEventListener('scroll', function() {
                if (!manualScroll) {
                    manualScroll = true;
                    // This is a manual scroll, allow it
                } else {
                    // This might be an auto-scroll, check if user initiated
                    setTimeout(() => { manualScroll = false; }, 100);
                }
            });
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

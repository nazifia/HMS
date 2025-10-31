(function($) {
    "use strict"; // Start of use strict

    // Function to toggle mobile sidebar - Manual only
    function toggleMobileSidebar() {
        const sidebar = $('#sidebar-container');
        const overlay = $('#sidebar-overlay');
        sidebar.toggleClass('sidebar-open');
        overlay.toggleClass('active');
        $('body').toggleClass('sidebar-open');
    }

    // Disable all auto-refresh, auto-reload, and auto-scroll functionality
    $(document).ready(function() {
        // Force sidebar to stay at top - no auto-scroll
        $('#sidebar-container').scrollTop(0);
        
        // Completely disable Bootstrap's auto-scroll for accordion
        $('#accordionSidebar .collapse').off('show.bs.collapse').on('show.bs.collapse', function(e) {
            e.stopPropagation();
            e.preventDefault();
            // Manual toggle only - prevent any automatic behaviors
            return false;
        });
        
        // Disable any auto-refresh intervals
        if (typeof window.sidebarRefreshInterval !== 'undefined') {
            clearInterval(window.sidebarRefreshInterval);
        }
        if (typeof window.sidebarUpdateInterval !== 'undefined') {
            clearInterval(window.sidebarUpdateInterval);
        }
        
        // Disable any hash-based scrolling
        if (window.location.hash) {
            window.scrollTo(0, 0);
            $('#sidebar-container').scrollTop(0);
        }
        
        // Remove any data attributes that might trigger auto-behaviors
        $('#sidebar-container, #accordionSidebar').removeAttr('data-refresh-url data-auto-refresh data-interval');
        
        // Override scrollIntoView for all sidebar elements
        $('#sidebar-container *').each(function() {
            if (this.scrollIntoView) {
                this.scrollIntoView = function() { return false; };
            }
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

    // Manual responsive behavior - no auto-resize triggers
    let resizeTimer;
    $(window).off('resize').on('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            // Only manual resize actions
            enforceManualOperation();
        }, 250);
    });

    // Manual sidebar scrolling only - no auto-behaviors
    $('#sidebar-container').on('wheel mousewheel DOMMouseScroll', function(e) {
        if ($(window).width() > 768) {
            this._userScrolling = true;
            setTimeout(() => { this._userScrolling = false; }, 150);
        }
    });

    // Complete manual-only sidebar operation
    function enforceManualOperation() {
        // Disable all potential auto-scroll triggers
        if (window.location.hash) {
            window.history.replaceState('', document.title, window.location.pathname);
        }
        
        // Force disable scrollIntoView for all sidebar elements
        document.querySelectorAll('#sidebar-container *, #accordionSidebar *').forEach(function(element) {
            if (element.scrollIntoView) {
                element.scrollIntoView = function() { return false; };
            }
        });
        
        // Force sidebar to stay at top always
        const sidebar = document.getElementById('sidebar-container');
        if (sidebar) {
            sidebar.scrollTop = 0;
            // Override any scroll changes that aren't user-initiated
            Object.defineProperty(sidebar, 'scrollTop', {
                set: function(value) {
                    // Only allow scroll if it's a manual user interaction
                    if (this._userScrolling) {
                        this._scrollTop = value;
                    }
                },
                get: function() {
                    return this._scrollTop || 0;
                }
            });
        }
    }

    // Apply manual-only operation
    $(document).ready(function() {
        enforceManualOperation();
        
        // Remove any auto-refresh, auto-update capabilities
        if (window.sidebarInterval) clearInterval(window.sidebarInterval);
        if (window.updateInterval) clearInterval(window.updateInterval);
        
        // Manual dropdown toggle only - prevent auto-opening
        $('.nav-link[data-bs-toggle="collapse"]').off('click').on('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const target = $(this).attr('data-bs-target');
            $(target).collapse('toggle');
            // Immediately force sidebar back to top to prevent any auto-scroll
            $('#sidebar-container').scrollTop(0);
        });
        
        // Prevent any form submissions that might trigger sidebar updates
        $('form').off('submit').on('submit', function(e) {
            // Allow normal form submission but prevent sidebar auto-updates
            return true;
        });
        
        // Force manual scroll position after any potential triggers
        setInterval(function() {
            const sidebar = document.getElementById('sidebar-container');
            if (sidebar && sidebar.scrollTop !== 0) {
                // If sidebar scrolled without user interaction, reset to top
                if (!sidebar._userScrolling) {
                    sidebar.scrollTop = 0;
                }
            }
        }, 100);

    // Disable scroll-to-top button auto-appear (manual only)
    $('.scroll-to-top').hide();

    // Manual scroll-to-top only if explicitly clicked
    $(document).off('click', 'a.scroll-to-top').on('click', 'a.scroll-to-top', function(e) {
        e.preventDefault();
        window.scrollTo(0, 0);
    });

})(jQuery); // End of use strict

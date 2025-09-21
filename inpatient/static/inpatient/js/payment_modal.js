// Payment Modal JavaScript for Outstanding Admission Payments
class PaymentModal {
    constructor(modalSelector) {
        this.modal = $(modalSelector);
        this.form = $('#paymentForm');
        this.loading = $('#paymentLoading');
        this.success = $('#paymentSuccess');
        this.error = $('#paymentError');
        this.processBtn = $('#processPaymentBtn');
        this.confirmCheckbox = $('#confirmPayment');

        this.admissionId = null;
        this.outstandingAmount = 0;
        this.walletBalance = 0;

        this.init();
    }

    init() {
        this.bindEvents();
        this.updateConfirmButton();
    }

    bindEvents() {
        // Confirm checkbox change
        this.confirmCheckbox.on('change', () => {
            this.updateConfirmButton();
        });

        // Process payment button click
        this.processBtn.on('click', (e) => {
            e.preventDefault();
            this.processPayment();
        });

        // Modal show event
        this.modal.on('show.bs.modal', (e) => {
            const button = $(e.relatedTarget);
            this.admissionId = button.data('admission-id');
            this.loadPaymentData();
        });

        // Modal hide event
        this.modal.on('hidden.bs.modal', () => {
            this.resetModal();
        });
    }

    updateConfirmButton() {
        const isChecked = this.confirmCheckbox.is(':checked');
        this.processBtn.prop('disabled', !isChecked);

        if (isChecked) {
            this.processBtn.removeClass('btn-primary').addClass('btn-success');
        } else {
            this.processBtn.removeClass('btn-success').addClass('btn-primary');
        }
    }

    loadPaymentData() {
        // Show loading state
        this.showLoading();

        // Get admission data from the page
        const admissionData = this.getAdmissionDataFromPage();

        if (admissionData) {
            this.populateModal(admissionData);
            this.hideLoading();
        } else {
            this.showError('Could not load admission data. Please refresh the page and try again.');
        }
    }

    getAdmissionDataFromPage() {
        try {
            // Get data from the financial summary cards
            const walletBalanceText = $('.card.border-left-success .h5').first().text();
            const outstandingBalanceText = $('.card.border-left-danger .h5').first().text();

            const walletBalance = this.parseCurrency(walletBalanceText);
            const outstandingAmount = this.parseCurrency(outstandingBalanceText);

            if (walletBalance === null || outstandingAmount === null) {
                return null;
            }

            // Get patient name
            const patientName = $('#modalPatientName').text() || 'Unknown Patient';

            return {
                walletBalance: walletBalance,
                outstandingAmount: outstandingAmount,
                patientName: patientName
            };
        } catch (error) {
            console.error('Error getting admission data:', error);
            return null;
        }
    }

    parseCurrency(text) {
        // Extract number from currency string like "₦3,900.11"
        const match = text.match(/₦([0-9,]+\.?[0-9]*)/);
        if (match) {
            return parseFloat(match[1].replace(/,/g, ''));
        }
        return null;
    }

    populateModal(data) {
        this.walletBalance = data.walletBalance;
        this.outstandingAmount = data.outstandingAmount;

        // Update modal content
        $('#modalWalletBalance').text('₦' + this.formatCurrency(data.walletBalance));
        $('#modalOutstandingAmount').text('₦' + this.formatCurrency(data.outstandingAmount));
        $('#confirmAmount').text('₦' + this.formatCurrency(data.outstandingAmount));

        // Update wallet status badge
        const walletStatus = $('#walletStatus');
        if (data.walletBalance >= data.outstandingAmount) {
            walletStatus.html('<span class="badge bg-success mt-2">Sufficient Funds</span>');
            $('#insufficientFundsWarning').hide();
        } else {
            walletStatus.html('<span class="badge bg-warning mt-2">Insufficient Funds</span>');
            $('#insufficientFundsWarning').show();
        }

        // Update payment impact information
        this.updatePaymentImpact();
    }

    updatePaymentImpact() {
        const impactDiv = $('#paymentImpact');
        const confirmAmount = this.outstandingAmount;

        if (this.walletBalance >= this.outstandingAmount) {
            const balanceAfter = this.walletBalance - this.outstandingAmount;
            impactDiv.html(`
                <p class="mb-1">✓ Wallet covers full outstanding amount</p>
                <p class="mb-1">✓ Balance after payment: <strong>₦${this.formatCurrency(balanceAfter)}</strong></p>
                <p class="mb-0">✓ Outstanding balance will be cleared</p>
            `);
        } else {
            const amountToPay = this.walletBalance;
            const remainingOutstanding = this.outstandingAmount - this.walletBalance;
            impactDiv.html(`
                <p class="mb-1">⚠ Wallet covers partial amount</p>
                <p class="mb-1">✓ Amount to be paid: <strong>₦${this.formatCurrency(amountToPay)}</strong></p>
                <p class="mb-0">⚠ Remaining outstanding: <strong>₦${this.formatCurrency(remainingOutstanding)}</strong></p>
            `);
        }
    }

    formatCurrency(amount) {
        return amount.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    async processPayment() {
        if (!this.admissionId) {
            this.showError('Admission ID not found. Please refresh the page and try again.');
            return;
        }

        // Show loading state
        this.showLoading();

        try {
            const response = await fetch(`/inpatient/admissions/${this.admissionId}/payment/ajax-process-outstanding/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken(),
                },
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess(result.message, result.data);
                this.updatePageData(result.data);
            } else {
                this.showError(result.message);
            }
        } catch (error) {
            console.error('Payment processing error:', error);
            this.showError('An error occurred while processing the payment. Please try again.');
        }
    }

    getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    showLoading() {
        this.form.hide();
        this.success.hide();
        this.error.hide();
        this.loading.show();
        this.processBtn.prop('disabled', true);
    }

    hideLoading() {
        this.loading.hide();
        this.form.show();
        this.processBtn.prop('disabled', false);
    }

    showSuccess(message, data) {
        this.form.hide();
        this.loading.hide();
        this.error.hide();
        this.success.show();

        // Update success message with actual amounts
        const successContent = this.success.find('.alert-heading').next('p');
        if (data) {
            const paymentType = data.is_partial_payment ? 'Partial payment' : 'Outstanding payment';
            successContent.html(`
                ${paymentType} of ₦${this.formatCurrency(data.amount_paid)} has been processed from the patient's wallet.<br>
                <small class="text-muted">
                    Wallet balance: ₦${this.formatCurrency(data.wallet_balance)} |
                    Outstanding: ₦${this.formatCurrency(data.outstanding_amount)}
                </small>
            `);
        }

        // Auto-close modal after 3 seconds
        setTimeout(() => {
            this.modal.modal('hide');
        }, 3000);
    }

    showError(message) {
        this.form.hide();
        this.loading.hide();
        this.success.hide();
        this.error.show();
        $('#errorMessage').text(message);
    }

    updatePageData(data) {
        // Update wallet balance on the page
        const walletCard = $('.card.border-left-success .h5').first();
        if (walletCard.length) {
            walletCard.text('₦' + this.formatCurrency(data.wallet_balance));
        }

        // Update outstanding balance on the page
        const outstandingCard = $('.card.border-left-danger .h5').first();
        if (outstandingCard.length) {
            outstandingCard.text('₦' + this.formatCurrency(data.outstanding_amount));

            // Update the badge text
            const badgeContainer = outstandingCard.closest('.card-body').find('.text-muted');
            if (badgeContainer.length) {
                if (data.outstanding_amount > 0) {
                    badgeContainer.text('Still owed');
                } else {
                    badgeContainer.text('Fully paid');
                }
            }
        }

        // Update payment status alert
        const paymentStatusAlert = $('.alert-warning, .alert-success').first();
        if (paymentStatusAlert.length) {
            const alertText = paymentStatusAlert.find('p').first();
            if (alertText.length) {
                if (data.outstanding_amount > 0) {
                    alertText.html(`
                        <strong>Total Cost:</strong> ₦${this.formatCurrency(data.outstanding_amount + data.amount_paid)} |
                        <strong>Paid from Wallet:</strong> ₦${this.formatCurrency(data.amount_paid)} |
                        <strong>Outstanding:</strong> ₦${this.formatCurrency(data.outstanding_amount)}
                    `);
                } else {
                    alertText.html('This admission has been fully paid through wallet deductions.');
                    paymentStatusAlert.removeClass('alert-warning').addClass('alert-success');
                }
            }
        }

        // Hide the payment button if outstanding is zero
        if (data.outstanding_amount <= 0) {
            const paymentButtons = $('a[href*="process-outstanding"], button[data-target="#paymentModal"]');
            paymentButtons.hide();
        }

        // Add animation to updated cards
        this.animateUpdatedCards();
    }

    animateUpdatedCards() {
        const cards = $('.card.border-left-success, .card.border-left-danger');
        cards.each(function(index) {
            $(this).css({
                'transform': 'scale(1.02)',
                'transition': 'transform 0.3s ease'
            });

            setTimeout(() => {
                $(this).css('transform', 'scale(1)');
            }, 300);
        });
    }

    resetModal() {
        this.form.show();
        this.loading.hide();
        this.success.hide();
        this.error.hide();
        this.confirmCheckbox.prop('checked', false);
        this.updateConfirmButton();
        $('#insufficientFundsWarning').hide();
    }
}

// Initialize payment modal when document is ready
$(document).ready(function() {
    // Initialize payment modal if it exists
    if ($('#paymentModal').length) {
        const paymentModal = new PaymentModal('#paymentModal');

        // Add click handler to payment buttons
        $('button[data-target="#paymentModal"]').on('click', function() {
            const admissionId = $(this).data('admission-id');
            if (admissionId) {
                $('#paymentModal').attr('data-admission-id', admissionId);
            }
        });
    }
});
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .models import Surgery, PostOperativeNote
from .forms import PostOperativeNoteForm

class PostOperativeNoteCreateView(LoginRequiredMixin, CreateView):
    model = PostOperativeNote
    form_class = PostOperativeNoteForm
    template_name = 'theatre/post_op_note_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['surgery'] = get_object_or_404(Surgery, pk=self.kwargs['surgery_id'])
        return context
    
    def form_valid(self, form):
        form.instance.surgery = get_object_or_404(Surgery, pk=self.kwargs['surgery_id'])
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Post-operative note added successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('theatre:surgery_detail', kwargs={'pk': self.kwargs['surgery_id']})

class PostOperativeNoteUpdateView(LoginRequiredMixin, UpdateView):
    model = PostOperativeNote
    form_class = PostOperativeNoteForm
    template_name = 'theatre/post_op_note_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['surgery'] = self.object.surgery
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Post-operative note updated successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('theatre:surgery_detail', kwargs={'pk': self.object.surgery.id})

class PostOperativeNoteDeleteView(LoginRequiredMixin, DeleteView):
    model = PostOperativeNote
    template_name = 'theatre/post_op_note_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['surgery'] = self.object.surgery
        return context
    
    def get_success_url(self):
        surgery_id = self.object.surgery.id
        messages.success(self.request, 'Post-operative note deleted successfully.')
        return reverse_lazy('theatre:surgery_detail', kwargs={'pk': surgery_id})
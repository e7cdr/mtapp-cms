from rest_framework import serializers
from parler_rest.serializers import TranslatableModelSerializer
from parler_rest.fields import TranslatedFieldsField
from django.contrib.contenttypes.models import ContentType
from .models import (
    TourAvailability, CommunicationLog, Report, StaffTask, DashboardData, AutomatedAlert
)
from bookings.serializers import BookingSerializer

class TourAvailabilitySerializer(TranslatableModelSerializer):
    translations = TranslatedFieldsField(shared_model=TourAvailability)
    tour = serializers.SerializerMethodField()

    class Meta:
        model = TourAvailability
        fields = ['id', 'content_type', 'object_id', 'tour', 'current_slots', 'last_updated', 'translations']

    def get_tour(self, obj):
        if obj.tour:
            if obj.content_type.model == 'fulltour':
                from tours.serializers import FullTourSerializer
                return FullTourSerializer(obj.tour, context=self.context).data
            elif obj.content_type.model == 'landtour':
                from tours.serializers import LandTourSerializer
                return LandTourSerializer(obj.tour, context=self.context).data
            elif obj.content_type.model == 'daytour':
                from tours.serializers import DayTourSerializer
                return DayTourSerializer(obj.tour, context=self.context).data
        return None

class CommunicationLogSerializer(TranslatableModelSerializer):
    translations = TranslatedFieldsField(shared_model=CommunicationLog)
    entity = serializers.SerializerMethodField()

    class Meta:
        model = CommunicationLog
        fields = [
            'id', 'entity_type', 'content_type', 'entity_id', 'entity', 'staff_name',
            'method', 'contact_date', 'follow_up_needed', 'follow_up_date', 'translations'
        ]

    def get_entity(self, obj):
        if obj.entity_type == 'booking':
            from bookings.serializers import BookingSerializer
            return BookingSerializer(obj.entity, context=self.context).data
        elif obj.entity_type == 'partner':
            from partners.serializers import PartnerSerializer
            return PartnerSerializer(obj.entity, context=self.context).data
        return None

class ReportSerializer(TranslatableModelSerializer):
    translations = TranslatedFieldsField(shared_model=Report)
    created_by = serializers.StringRelatedField()

    class Meta:
        model = Report
        fields = [
            'id', 'report_type', 'data', 'start_date', 'end_date', 'generated_date',
            'created_by', 'translations'
        ]

class StaffTaskSerializer(TranslatableModelSerializer):
    translations = TranslatedFieldsField(shared_model=StaffTask)
    assigned_to = serializers.StringRelatedField()
    related_booking = BookingSerializer(read_only=True)

    class Meta:
        model = StaffTask
        fields = [
            'id', 'priority', 'status', 'due_date', 'assigned_to', 'related_booking',
            'created_at', 'updated_at', 'translations'
        ]

class DashboardDataSerializer(TranslatableModelSerializer):
    translations = TranslatedFieldsField(shared_model=DashboardData)

    class Meta:
        model = DashboardData
        fields = ['id', 'value', 'last_updated', 'translations']

class AutomatedAlertSerializer(TranslatableModelSerializer):
    translations = TranslatedFieldsField(shared_model=AutomatedAlert)
    related_object = serializers.SerializerMethodField()

    class Meta:
        model = AutomatedAlert
        fields = [
            'id', 'alert_type', 'triggered_date', 'is_resolved', 'related_object_type',
            'related_object_id', 'related_object', 'translations'
        ]

    def get_related_object(self, obj):
        if obj.related_object:
            content_type = obj.related_object_type
            if content_type.model == 'booking':
                from bookings.serializers import BookingSerializer
                return BookingSerializer(obj.related_object, context=self.context).data
            # Add other types as needed (e.g., StaffTask)
        return None
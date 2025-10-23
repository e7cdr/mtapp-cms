from rest_framework import serializers
from parler_rest.serializers import TranslatableModelSerializer
from parler_rest.fields import TranslatedFieldsField
from .models import FullTour, LandTour, DayTour, Amenity, CancellationPolicy

class AmenitySerializer(TranslatableModelSerializer):
    translations = TranslatedFieldsField(shared_model=Amenity)

    class Meta:
        model = Amenity
        fields = ['id', 'translations']

class CancellationPolicySerializer(TranslatableModelSerializer):
    translations = TranslatedFieldsField(shared_model=CancellationPolicy)

    class Meta:
        model = CancellationPolicy
        fields = ['id', 'days_before', 'refund_percentage', 'translations']

class FullTourSerializer(TranslatableModelSerializer):
    translations = TranslatedFieldsField(shared_model=FullTour)
    amenities = AmenitySerializer(many=True, read_only=True)
    cancellation_policy = CancellationPolicySerializer(read_only=True)

    class Meta:
        model = FullTour
        fields = [
            'id', 'code_id', 'ref_code', 'duration_days', 'nights', 'start_date', 'end_date',
            'is_all_inclusive', 'price_sgl_regular', 'price_dbl_regular', 'price_tpl_regular',
            'price_chd_regular', 'max_capacity', 'available_slots', 'created_at', 'updated_at',
            'amenities', 'cancellation_policy', 'translations'
        ]

class LandTourSerializer(TranslatableModelSerializer):
    translations = TranslatedFieldsField(shared_model=LandTour)
    amenities = AmenitySerializer(many=True, read_only=True)
    cancellation_policy = CancellationPolicySerializer(read_only=True)

    class Meta:
        model = LandTour
        fields = [
            'id', 'code_id', 'ref_code', 'duration_days', 'nights', 'start_date', 'end_date',
            'price_sgl', 'price_dbl', 'price_tpl', 'price_chd', 'max_capacity', 'available_slots',
            'created_at', 'updated_at', 'amenities', 'cancellation_policy', 'translations'
        ]

class DayTourSerializer(TranslatableModelSerializer):
    translations = TranslatedFieldsField(shared_model=DayTour)
    amenities = AmenitySerializer(many=True, read_only=True)
    cancellation_policy = CancellationPolicySerializer(read_only=True)

    class Meta:
        model = DayTour
        fields = [
            'id', 'code_id', 'ref_code', 'date', 'duration_hours', 'price_adult', 'price_child',
            'max_capacity', 'available_slots', 'created_at', 'updated_at', 'amenities',
            'cancellation_policy', 'translations'
        ]
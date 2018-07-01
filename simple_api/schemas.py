from marshmallow import Schema, fields


class FoodSchema(Schema):
    id = fields.Integer(dump_only=True)     # dump only field, db provides
    name = fields.Str(required=True)
    food_type = fields.Str(required=True)


class FoodPatchSchema(Schema):
    food_type = fields.Str(required=True)       # can only update food_type

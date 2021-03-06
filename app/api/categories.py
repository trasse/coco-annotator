from flask_restplus import Namespace, Resource, reqparse
from flask_login import login_required, current_user
from mongoengine.errors import NotUniqueError

from ..util.pagination_util import Pagination
from ..util import query_util
from ..models import CategoryModel, AnnotationModel

import datetime

api = Namespace('category', description='Category related operations')

create_category = reqparse.RequestParser()
create_category.add_argument('name', required=True, location='json')
create_category.add_argument('supercategory', location='json')
create_category.add_argument('color',  location='json')
create_category.add_argument('metadata', type=dict, location='json')

page_data = reqparse.RequestParser()
page_data.add_argument('page', default=1, type=int)
page_data.add_argument('limit', default=20, type=int)


@api.route('/')
class Category(Resource):

    @login_required
    def get(self):
        """ Returns all categories """
        return query_util.fix_ids(current_user.categories.all())

    @api.expect(create_category)
    @login_required
    def post(self):
        """ Creates a category """
        args = create_category.parse_args()
        name = args.get('name')
        supercategory = args.get('supercategory')
        metadata = args.get('metadata', {})
        color = args.get('color')
        
        try:
            category = CategoryModel(
                name=name,
                supercategory=supercategory,
                color=color,
                metadata=metadata
            )
            category.save()
        except NotUniqueError as e:
            return {'message': 'Category already exists. Check the undo tab to fully delete the category.'}, 400

        return query_util.fix_ids(category)


@api.route('/<int:category_id>')
class Category(Resource):

    @login_required
    def get(self, category_id):
        """ Returns a category by ID """
        category = current_user.categories.filter(id=category_id).first()

        if category is None:
            return {'success': False}, 400

        return query_util.fix_ids(category)

    @login_required
    def delete(self, category_id):
        """ Deletes a category by ID """
        category = current_user.categories.filter(id=category_id).first()
        if category is None:
            return {"message": "Invalid image id"}, 400
        
        if not current_user.can_delete(category):
            return {"message": "You do not have permission to download the dataset's annotations"}, 403

        category.update(set__deleted=True, set__deleted_date=datetime.datetime.now())
        return {'success': True}


@api.route('/data')
class CategoriesData(Resource):

    @api.expect(page_data)
    @login_required
    def get(self):
        """ Endpoint called by category viewer client """
        args = page_data.parse_args()
        limit = args['limit']
        page = args['page']

        categories = current_user.categories.filter(deleted=False)

        pagination = Pagination(categories.count(), limit, page)
        categories = query_util.fix_ids(categories[pagination.start:pagination.end])

        for category in categories:
            category['numberAnnotations'] = AnnotationModel.objects(deleted=False, category_id=category.get('id')).count()

        return {
            "pagination": pagination.export(),
            "page": page,
            "categories": categories
        }

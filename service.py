#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, Response, jsonify, redirect, stream_with_context, send_from_directory
import argparse
from glob import glob
import os
import json
from PIL import Image
from io import BytesIO
import base64
import numpy as np
from collections import Counter


app = Flask(__name__)
directory = None
annotation = None
labels = None
visible_labels = None
images = None


def stream_template(template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.disable_buffering()
    return rv


def count_labeled():
    global annotation
    return len(annotation['labeling'])


def count_labeled_for_labels():
    global annotation
    counter = Counter()
    for selected_labels in annotation['labeling'].values():
        counter.update(selected_labels)
    return counter


def count_unlabeled():
    global images
    if images is None:
        load_images_paths()
    return len(images) - count_labeled()


def check_args(args):
    assert os.path.exists(args.directory), "Указанная директория не существует!"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--directory', required=True, help='[Required] Директория с изображениями')
    parser.add_argument('-p', '--port', default=1100, help='Порт для работы сервиса')
    args = parser.parse_args()
    check_args(args)
    return args


def file_is_image(path):
    path = path.lower()
    return path.endswith('.jpeg') or path.endswith('.jpg') or path.endswith('.bmp') or path.endswith('.png')


def image_is_unlabeled(path):
    return path not in annotation['labeling']


def image_to_base64(image):
    jpeg_image_buffer = BytesIO()
    image.save(jpeg_image_buffer, format="JPEG")
    bytes_image = base64.b64encode(jpeg_image_buffer.getvalue())
    return bytes_image.decode('ascii')


def path_to_base64(relative_path):
    global annotation
    return image_to_base64(Image.open(os.path.join(annotation['directory'], relative_path)))


def labels_path():
    global directory
    if isinstance(directory, str):
        return os.path.join(directory, 'labels.json')
    return None


def annotation_path():
    global directory
    if isinstance(directory, str):
        return os.path.join(directory, 'annotation.json')
    return None


def image_abs_path(relative_path):
    global annotation
    return os.path.join(annotation['directory'], relative_path)


def load_images_paths():
    global images, directory
    images = list(map(lambda x: os.path.relpath(x, directory),
                      filter(file_is_image, sorted(glob(pathname=directory + '/**/*', recursive=True)))))


def load_labels():
    global labels, visible_labels
    path = labels_path()
    if isinstance(path, str):
        assert os.path.isfile(path), "File with labels doesn't exist!"
        with open(path, 'r') as f:
            data = json.load(f)
            labels = data['labels']
            if 'visible_labels' in data:
                visible_labels = data['visible_labels']
            else:
                visible_labels = {label: label for label in labels}
    else:
        raise FileNotFoundError


def load_annotation():
    global annotation, images, directory
    path = annotation_path()
    if os.path.exists(path):
        with open(annotation_path()) as f:
            annotation = json.load(f)
        annotation['directory'] = directory
        if images is None:
            load_images_paths()
        for path in [path for path in annotation['labeling'].keys() if path not in images]:
            annotation['missed'][path] = annotation['labeling'][path]
            del annotation['labeling'][path]
        save_annotation()
    else:
        annotation = {'directory': directory, 'labeling': dict(), 'missed': dict()}


def save_annotation():
    global annotation
    with open(annotation_path(), 'w') as f:
        json.dump(annotation, f)


def load_data():
    load_images_paths()
    load_labels()
    load_annotation()


def ok_response():
    return jsonify({'success': True})


@app.route('/editing_labels', methods=['POST'])
def edit_labels():
    params = request.json
    global directory, labels, visible_labels, annotation, images
    image = Image.open(image_abs_path(params['path']))
    selected_labels = annotation['labeling'][params['path']] if params['path'] in annotation['labeling'] else []
    return render_template('editing_page.html',
                           image_base64=image_to_base64(image),
                           image_path=params['path'],
                           n_images=len(images),
                           n_unlabeled=count_unlabeled(),
                           n_labeled=count_labeled(),
                           selected_labels=selected_labels,
                           labels=labels,
                           visible_labels=visible_labels)


@app.route('/save', methods=['POST'])
def save_image():
    params = request.json
    annotation['labeling'][params['path']] = params['classes']
    save_annotation()
    return ok_response()


@app.route('/clear_labeling', methods=['POST'])
def clear_labeling():
    params = request.json
    if params['path'] in annotation['labeling']:
        del annotation['labeling'][params['path']]
        save_annotation()
    return ok_response()


@app.route('/delete', methods=['POST'])
def delete_image():
    global images
    path = request.json['path']
    if path in images:
        images.remove(path)
    if os.path.exists(path):
        os.remove(path)
    if path in annotation['labeling']:
        del annotation['labeling'][path]
    return ok_response()


@app.route('/reload', methods=['POST'])
def reload_images():
    load_data()
    return ok_response()


@app.route('/')
def index():
    load_data()
    return redirect('/next')


@app.route('/next')
def next_image():
    global directory, labels, visible_labels, images
    if images is None:
        load_images_paths()
    if count_unlabeled():
        unlabeled = list(filter(image_is_unlabeled, images))
        image_path = np.random.choice(unlabeled)
        image = Image.open(image_abs_path(image_path))
        page = render_template('labeling_page.html',
                               image_base64=image_to_base64(image),
                               image_path=image_path,
                               n_images=len(images),
                               n_unlabeled=count_unlabeled(),
                               n_labeled=count_labeled(),
                               labels=labels,
                               visible_labels=visible_labels)
    else:
        page = render_template('no_unlabeled.html')
    return page


def ending(number):
    mod = number % 100
    if 10 < mod < 20:
        return 'ий'
    mod = mod % 10
    if 5 <= mod <= 9 or mod == 0:
        return 'ий'
    if 2 <= mod <= 4:
        return 'ия'
    return 'ие'


@app.route('/labeled', methods=['GET', 'POST'])
def labeled_images():
    global annotation, labels, visible_labels, images
    args = request.args
    if 'labels' in args:
        selected_labels = set(args['labels'].split(','))
        labeling = {path: labeled for path, labeled in annotation['labeling'].items()
                    if set(labeled).intersection(selected_labels)}
    else:
        labeling = annotation['labeling']
        selected_labels = []
    if images is None:
        load_images_paths()
    perpage = int(args['perpage']) if 'perpage' in args else 25
    perpage = min(100, max(1, perpage))
    page = int(args['page']) if 'page' in args else 1
    max_page = (count_labeled()+perpage-1) // perpage
    page = min(max_page, max(1, page))
    # Select for page
    labels_count = count_labeled_for_labels()
    labeling = dict(sorted(labeling.items())[(page - 1) * perpage:page * perpage])
    return Response(stream_with_context(stream_template('preview_images.html',
                                                        page_type='labeled',
                                                        labeling=labeling,
                                                        path_to_base64=path_to_base64,
                                                        n_images=len(images),
                                                        n_unlabeled=count_unlabeled(),
                                                        n_labeled=count_labeled(),
                                                        visible_labels=visible_labels,
                                                        labels=list(map(lambda x: x[0], labels_count.most_common())),
                                                        selected_labels=selected_labels,
                                                        labels_count=labels_count,
                                                        page=page,
                                                        max_page=max_page,
                                                        ending=ending,
                                                        n_found=count_labeled(),
                                                        perpage=perpage)))


@app.route('/unlabeled', methods=['GET', 'POST'])
def unlabeled_images():
    global annotation, labels, visible_labels, images
    args = request.args
    if images is None:
        load_images_paths()
    unlabeled = list(filter(image_is_unlabeled, images))
    perpage = int(args['perpage']) if 'perpage' in args else 25
    perpage = min(100, max(1, perpage))
    page = int(args['page']) if 'page' in args else 1
    max_page = (count_unlabeled()+perpage-1)//perpage
    page = min(max_page, max(1, page))
    labeling = {x: {} for x in unlabeled[(page-1)*perpage:page*perpage]}
    return Response(stream_with_context(stream_template('preview_images.html',
                                                        page_type='unlabeled',
                                                        labeling=labeling,
                                                        path_to_base64=path_to_base64,
                                                        n_images=len(images),
                                                        n_unlabeled=count_unlabeled(),
                                                        n_labeled=count_labeled(),
                                                        visible_labels=visible_labels,
                                                        page=page,
                                                        max_page=max_page,
                                                        ending=ending,
                                                        n_found=count_unlabeled(),
                                                        perpage=perpage)))


@app.route('/robots.txt')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])


def main():
    global directory
    args = parse_args()
    directory = os.path.abspath(args.directory)
    load_data()
    app.run(host='0.0.0.0', debug=True, threaded=False, port=args.port)


if __name__ == '__main__':
    main()

var Direction = {
  LEFT: 0,
  UP: 1,
  RIGHT: 2,
  DOWN: 3
};

var Rectangle = (function () {
  function Rectangle(canvas, src, crop) {
    var inst = this;
    this.canvas = canvas;
    this.image = null;
    this.zoomLevel = 0;
    this.zoomLevelMin = 0;
    this.zoomLevelMax = 3;
    this.scaledSize = null;
    this.scaleInfor = null;
    this.mouseDownPoint = null;
    this.mouseStart = null;
    this.labels = [];
    this.started = false;
    this.x = null;
    this.y = null;
    this.shiftKeyDown = false;
    this.cropped = crop;
    if (this.cropped) {
      this.ctx = this.cropped.getContext('2d');
    }
    this.bindEvents();
    this.canvas.selection = false;
    fabric.Image.fromURL(src, img => {
      inst.image = img;
      inst._drawImage(img);
    });
    fabric.util.addListener(document.body, 'keyup', function (options) {
      var key = options.which || options.keyCode;
      if (key == 16) {
        inst.canvas.defaultCursor = 'default';
        inst.shiftKeyDown = false;
      }
    });
    fabric.util.addListener(document.body, 'keydown', function (options) {
      inst.canvas.fire('custom:keydom', options);
      if (options.repeat) {
        return;
      }
      var key = options.which || options.keyCode;
      if (key == 16) {
        inst.canvas.defaultCursor = 'move';
        inst.canvas.selection = false;
        inst.shiftKeyDown = true;
      } else if (key === 37) {
        inst.move(Direction.LEFT);
      } else if (key === 38) {
        inst.move(Direction.UP);
      } else if (key === 39) {
        inst.move(Direction.RIGHT);
      } else if (key === 40) {
        inst.move(Direction.DOWN);
      }
    });
  }

  Rectangle.prototype._getScaleImageInfo = function (imgWidth, imgHeight, maxWidth, maxHeight) {
    let wRatio = maxWidth / imgWidth;
    let hRatio = maxHeight / imgHeight;
    let scale = 1;
    if (imgWidth > maxWidth && wRatio < hRatio) {
      scale = wRatio;
    } else if (imgHeight > maxHeight && hRatio < wRatio) {
      scale = hRatio;
    }

    let width = Number((imgWidth * scale).toFixed(0));
    let height = Number((imgHeight * scale).toFixed(0));

    return {width, height, scale};
  };
  Rectangle.prototype._drawImage = function (image) {
    if (!image) {
      return;
    }
    var self = this;
    this.image = image;
    this.scaledSize = this._getScaleImageInfo(image.width, image.height, this.canvas.width, this.canvas.height);
    this.canvas.setWidth(this.scaledSize.width);
    this.canvas.setHeight(this.scaledSize.height);
    this.canvas.calcOffset();
    let scaleX = this.canvas.width / image.width;
    let scaleY = this.canvas.height / image.height;
    this.canvas.setBackgroundImage(image, self.canvas.renderAll.bind(self.canvas), {
      scaleX: scaleX,
      scaleY: scaleY
    });
    this.drawSuccess.call();
  };
  Rectangle.prototype.bindEvents = function () {
    var inst = this;
    inst.canvas.on('mouse:down', function (o) {
      inst.onMouseDown(o);
    });
    inst.canvas.on('mouse:move', function (o) {
      inst.onMouseMove(o);
    });
    inst.canvas.on('mouse:up', function (o) {
      inst.onMouseUp(o);
    });
    inst.canvas.on('object:moving', function (o) {
      inst.disable();
    });
    inst.canvas.on('custom:keydom', event => {
      if (event.keyCode == 46) {
        inst.removeLabel(inst.canvas.getActiveObject());
      }
      if (event.keyCode == 16) {
        inst.shiftKeyDown = true
      } else {
        inst.shiftKeyDown = false
      }
      if (event.ctrlKey && event.keyCode == 68) {
          event.preventDefault();
          inst.duplicate()
      }
    });
  };
  Rectangle.prototype.removeLabel = function (label) {
    if (!label) {
      return;
    }
    var self = this;
    self.labels = self.labels.filter(lab => lab !== label);
    self.canvas.remove(label);
    this.removeSuccess.call()
  };
  Rectangle.prototype.onMouseUp = function (options) {
    this.mouseDownPoint = null;
    this.started = false;
    var self = this;
    if (this.mouseStart != null) {
      this.labels.forEach(function (label) {
        if (label.height < 5 || label.width < 5) {
          self.removeLabel(label);
        }
      });
      this.boxCreated.call();
    }
    var pointer = self.canvas.getPointer(options.e, true);
    var point = new fabric.Point(pointer.x, pointer.y);
    this.canvas.zoomToPoint(point, Math.pow(2, this.zoomLevel));
    this.keepPositionInBounds();
    if (this.cropped) {
      this.cropImage();
    }
  };

  Rectangle.prototype.onMouseMove = function (options) {
    if (this.shiftKeyDown && this.mouseDownPoint != null) {
      var pointer = this.canvas.getPointer(options.e, true);
      var mouseMovePoint = new fabric.Point(pointer.x, pointer.y);
      this.canvas.relativePan(mouseMovePoint.subtract(this.mouseDownPoint));
      this.mouseDownPoint = mouseMovePoint;
      this.keepPositionInBounds();
    } else if (this.started) {
      var mouse = this.canvas.getPointer(options.e);

      var w = Math.abs(mouse.x - this.x),
          h = Math.abs(mouse.y - this.y);
      if (!w || !h) {
        return false;
      }
      var square = this.canvas.getActiveObject();
      square.set('width', w).set('height', h);
      this.canvas.renderAll();
    }
  };
  Rectangle.prototype.onMouseDown = function (options) {
    var pointer = this.canvas.getPointer(options.e, true);
    this.mouseDownPoint = new fabric.Point(pointer.x, pointer.y);

    if (!options.e.shiftKey) {
      if (!options.target) {
        this.mouseStart = options;
        var mouse = this.canvas.getPointer(options.e);
        this.started = true;
        this.x = mouse.x;
        this.y = mouse.y;
        var square = new fabric.Rect({
          left: this.x,
          top: this.y,
          originX: 'left',
          originY: 'top',
          width: 0,
          height: 0,
          hasRotatingPoint: false,
          stroke: 'red',
          strokeWidth: 0.5,
          fill: 'rgba(0,0,0,0.2)',
          cornerSize: 5,
          cornerStyle: 'circle',
          cornerColor: '#ff0000',
          borderColor: '#ff0000',
          transparentCorners: false,
          text: '',
          key: '',
          position: '',
          rows: 1,
          columns: 1,
          details: null,
          model: 'normal',
          display: 'yes',
        });

        square.on('modified', event => {
          this._adjustRectSizePosition(square);
        });
        this.canvas.add(square);
        this.canvas.renderAll();
        this.labels.push(square);
        this.canvas.setActiveObject(square);
      } else {
        this.mouseStart = null;
        this.callBack.call();
      }
    }
  };
  Rectangle.prototype.callBack = function () {
  };
  Rectangle.prototype.boxCreated = function () {
  };
  Rectangle.prototype.drawSuccess = function () {
  };
  Rectangle.prototype.removeSuccess = function () {
  };
  Rectangle.prototype.getScale = function () {
    return this.scaleInfor;
  };
  Rectangle.prototype.getScaleSized = function () {
    return this.scaledSize;
  };
  Rectangle.prototype.getImgWidthHeight = function () {
    return [this.image.width, this.image.height];
  };
  Rectangle.prototype.duplicate = function () {
    let rec = this.canvas.getActiveObject();
    if (rec) {
      this.addLabel(rec.left + 5, rec.top + 5, rec.width, rec.height)
    }
  };
  Rectangle.prototype.addLabel = function (x, y, w, h, size_w, size_h, text, columns, rows, key, details, position, model, display) {
    size_h = size_h == null ? this.image.height : size_h;
    size_w = size_h == null ? this.image.width : size_w;
    let scaledSize = this._getScaleImageInfo(size_w, size_h, this.canvas.width, this.canvas.height);
    let scale = scaledSize.scale;
    this.scaleInfor = scale;
    var square = new fabric.Rect({
      left:  Math.round(x * scale),
      top:  Math.round(y * scale),
      originX: 'left',
      originY: 'top',
      width:  Math.round(w * scale),
      height:  Math.round(h * scale),
      hasRotatingPoint: false,
      stroke: 'red',
      strokeWidth: 0.5,
      fill: 'rgba(0,0,0,0.2)',
      cornerSize: 5,
      cornerStyle: 'circle',
      cornerColor: '#ff0000',
      borderColor: '#ff0000',
      text: text,
      key: key == 0 ? 0 : key && key != null ? key : '',
      position: position && position != null ? position : '',
      rows: rows && rows != null ? rows : 1,
      columns: columns && columns != null ? columns : 1,
      details: details ? details : null,
      model: model ? model : 'normal',
      display: display ? display : 'yes',
    });
    square.on('modified', event => {
      this._adjustRectSizePosition(square);
    });
    this.canvas.add(square);
    this.canvas.renderAll();
    this.labels.push(square);
    this.canvas.setActiveObject(square);
    this.boxCreated.call();
  };
  Rectangle.prototype._adjustRectSizePosition = function (rect) {
    const minSize = 10;

    let width = rect.width * rect.scaleX;
    let height = rect.height * rect.scaleY;
    let left = rect.left;
    let top = rect.top;

    if (left >= this.canvas.width - minSize) {
      left = this.canvas.width - minSize;
    }
    if (top >= this.canvas.height - minSize) {
      top = this.canvas.height - minSize;
    }
    if (left + width > this.canvas.width) {
      width = this.canvas.width - left;
    }
    if (top + height > this.canvas.height) {
      height = this.canvas.height - top;
    }
    if (left < 0) {
      width += left;
      left = 0;
    }
    if (top < 0) {
      height += top;
      top = 0;
    }
    if (left + width < 0) {
      width = minSize;
    }
    if (top + height < 0) {
      height = minSize;
    }
    rect.set({
      left: left,
      top: top,
      width: width,
      height: height,
      scaleX: 1,
      scaleY: 1
    });
    rect.setCoords();
  };
  Rectangle.prototype.keepPositionInBounds = function () {
    var zoom = this.canvas.getZoom();
    var xMin = (2 - zoom) * this.canvas.getWidth() / 2;
    var xMax = zoom * this.canvas.getWidth() / 2;
    var yMin = (2 - zoom) * this.canvas.getHeight() / 2;
    var yMax = zoom * this.canvas.getHeight() / 2;

    var point = new fabric.Point(this.canvas.getWidth() / 2, this.canvas.getHeight() / 2);
    var center = fabric.util.transformPoint(point, this.canvas.viewportTransform);

    var clampedCenterX = this.clamp(center.x, xMin, xMax);
    var clampedCenterY = this.clamp(center.y, yMin, yMax);

    var diffX = clampedCenterX - center.x;
    var diffY = clampedCenterY - center.y;

    if (diffX != 0 || diffY != 0) {
      this.canvas.relativePan(new fabric.Point(diffX, diffY));
    }
  };
  Rectangle.prototype.isEnable = function () {
    return this.isDrawing;
  };

  Rectangle.prototype.enable = function () {
    this.isDrawing = true;
  };

  Rectangle.prototype.disable = function () {
    this.isDrawing = false;
  };

  Rectangle.prototype.zoomIn = function (point) {
    if (this.zoomLevel < this.zoomLevelMax) {
      this.zoomLevel += 0.1;
      this.canvas.zoomToPoint(point, Math.pow(2, this.zoomLevel));
      this.keepPositionInBounds();
    }
  };
  Rectangle.prototype.zoomOut = function (point) {
    if (this.zoomLevel > this.zoomLevelMin) {
      this.zoomLevel -= 0.05;
      this.canvas.zoomToPoint(point, Math.pow(2, this.zoomLevel));
      this.keepPositionInBounds();
    }
  };
  Rectangle.prototype.clamp = function (value, min, max) {
    return Math.max(min, Math.min(value, max));
  };
  Rectangle.prototype.selectObj = function (label) {
    this.canvas.setActiveObject(label);
    this.canvas.renderAll();
    // let rec = this.canvas.getActiveObject();
    // var point = new fabric.Point(rec.left, rec.top);
    // this.canvas.absolutePan(point);
    // this.keepPositionInBounds();
    if (this.ctx) {
      this.cropImage();
    }
  };
  Rectangle.prototype.move = function (direction) {
    switch (direction) {
      case Direction.LEFT:
        this.canvas.relativePan(new fabric.Point(-10 * this.canvas.getZoom(), 0));
        break;
      case Direction.UP:
        this.canvas.relativePan(new fabric.Point(0, -10 * this.canvas.getZoom()));
        break;
      case Direction.RIGHT:
        this.canvas.relativePan(new fabric.Point(10 * this.canvas.getZoom(), 0));
        break;
      case Direction.DOWN:
        this.canvas.relativePan(new fabric.Point(0, 10 * this.canvas.getZoom()));
        break;
    }
    this.keepPositionInBounds();
  };
  Rectangle.prototype.cropImage = function () {
    var self = this;
    this.ctx.clearRect(0, 0, self.cropped.width, self.cropped.height);
    var img = new Image();
    img.src = self.image._element.src;
    var rect = self.canvas.getActiveObject();
    if (rect && rect != null) {
      var left = rect.left / this.scaledSize.scale;
      var top = rect.top / this.scaledSize.scale;
      var width = rect.width / this.scaledSize.scale;
      var height = rect.height / this.scaledSize.scale;
      let scl = self._getScaleImageInfo(width, height, self.cropped.width, self.cropped.height);
      img.onload = function () {
        self.ctx.drawImage(img, left, top, width, height, 0, 0, scl.width, scl.height);
      }
    }
  };
  Rectangle.prototype.drawCropped = function (cav, box) {
    var self = this;
    let ctx = cav.getContext('2d');
    ctx.clearRect(0, 0, cav.width, cav.height);
    var img = new Image();
    img.src = self.image._element.src;
    var rect = box;
    if (rect && rect != null) {
      var left = rect.left / this.scaledSize.scale;
      var top = rect.top / this.scaledSize.scale;
      var width = rect.width / this.scaledSize.scale;
      var height = rect.height / this.scaledSize.scale;
      let scl = self._getScaleImageInfo(width, height, cav.width, cav.height);

      let dx = 0;
      if (width < cav.width) {
        dx = cav.width / 2 - rect.width;
      }
      img.onload = function () {
        ctx.drawImage(img, left, top, width, height, dx, 0, scl.width, scl.height);
      }
    }
  };
  Rectangle.prototype.drawCropped2 = async function (box) {
    var self = this;

    var rect = box;
    if (rect && rect != null) {
      var img = new Image();
      img.src = self.image._element.src;
      var left = rect.left / this.scaledSize.scale;
      var top = rect.top / this.scaledSize.scale;
      var width = rect.width / this.scaledSize.scale;
      var height = rect.height / this.scaledSize.scale;

      let cav = document.createElement('canvas');
      cav.id = 'test';
      cav.width = width;
      cav.height = height;
      let ctx = cav.getContext('2d');
      let scl = self._getScaleImageInfo(width, height, cav.width, cav.height);

      await new Promise(resolve => {
        img.onload = function () {
          ctx.drawImage(img, left, top, width, height, 0, 0, scl.width, scl.height);
          resolve('resolved');
        };
      });
      return cav.toDataURL('image/jpeg');
    }
  };
  Rectangle.prototype.clearLabel= function () {
    // let ctx = this.canvas.getContext('2d');
    for (let x of this.labels) {
      this.canvas.remove(x);
    }
    // ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  };
  Rectangle.prototype.clearAll = function () {
    let ctx = this.canvas.getContext('2d');
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  };
  return Rectangle;
}());
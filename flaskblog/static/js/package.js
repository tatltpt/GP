myObject = new Vue({
  el: '#package',
  data: {
    items: [],
    formats: null,
    default_type: null,
    files: null,
    itemName: null,
    file1: null,
    file2: null,
    pkgId: null,
    error: false,
    editedTodo: null
  },
  beforeMount: function () {
    this.items = localData.data;
    this.pkgId = window.location.href.split('?')[0].split('/').pop();
  },
  mounted() {
    this.socket = io.connect('/start_processing');
    this.socket.on('connected', function (msg) {
      console.log('After connect', msg);
    });
    this.socket.on('update value', function () {
      $('body').removeClass('loading');
      window.location.replace('/')
    });
  },
  methods: {
    selectFile1() {
      $('#files1').click();
    },
    selectFile2() {
      $('#files2').click();
    },
    selectDefault(type) {
      this.default_type = type.id
    },
    fileDragHover1(e) {
      var fileDrag = document.getElementById('upload-content-1');
      e.stopPropagation();
      e.preventDefault();
      fileDrag.className = (e.type === 'dragover' ? 'hover' : 'card-body');
    },
    fileDropHover1(e) {
      var fileDrag = document.getElementById('upload-content-1');
      fileDrag.className = 'card-body';
      let droppedFiles = e.dataTransfer.files;
      if (!droppedFiles) return;
      this.file1 = {
        'file': droppedFiles[0],
        'url': URL.createObjectURL(droppedFiles[0]),
        'name': droppedFiles[0].name,
        'edit': false
      };
    },
    fileDragHover2(e) {
      var fileDrag = document.getElementById('upload-content-2');
      e.stopPropagation();
      e.preventDefault();
      fileDrag.className = (e.type === 'dragover' ? 'hover' : 'card-body');
    },
    fileDropHover2(e) {
      var fileDrag = document.getElementById('upload-content-2');
      fileDrag.className = 'card-body';
      let droppedFiles = e.dataTransfer.files;
      if (!droppedFiles) return;
      this.file2 = {
        'file': droppedFiles[0],
        'url': URL.createObjectURL(droppedFiles[0]),
        'name': droppedFiles[0].name,
        'edit': false
      };
    },
    deleteItem(index) {
      var xhr = new XMLHttpRequest();
      var self = this;
      xhr.onload = function () {
        $('body').removeClass('loading');
        let data = JSON.parse(this.response);
        if (data.mess === 'success') {
          let id = self.items.findIndex(item => item.id == index);
          self.items.splice(id, 1);
        }
      };
      var fd = new FormData();
      fd.append("id", index);
      $('body').addClass('loading');
      xhr.open("POST", "/delete_item", true);
      xhr.send(fd);
    },
    editTodo: function (todo) {
      this.list = todo;
    },
    handleFilesUpload(e) {
      if (e.target.id == 'files1') {
        this.file1 = {
          'file': e.target.files[0],
          'url': URL.createObjectURL(e.target.files[0]),
          'name': e.target.files[0].name,
          'edit': false
        };
      } else if (e.target.id == 'files2') {
        this.file2 = {
          'file': e.target.files[0],
          'url': URL.createObjectURL(e.target.files[0]),
          'name': e.target.files[0].name,
          'edit': false
        };
      }
    },
    openUpload() {
      $("#upload-item").modal('toggle');
    },
    clear() {
      this.list = [];
    },
    deleteImg1() {
      this.file1 = null;
    },
    deleteImg2() {
      this.file2 = null;
    },
    upload() {
      var formData = new FormData();
      var self = this;
      if (this.file1 != null && this.file2 != null && this.itemName != null) {
        this.error = false;
        formData.append("file1", this.file1.file);
        formData.append("file2", this.file2.file);
        formData.append('name', this.itemName);
        formData.append('pkg_id', this.pkgId);
        $('body').addClass("loading");
        $.ajax({
          url: "/create_item",
          type: "POST",
          data: formData,
          mimeTypes: "multipart/form-data",
          contentType: false,
          processData: false,
          success: function (e) {
            $('body').removeClass("loading");
            $("#upload-item").modal('toggle');
            if (e.mess === "success") {
              self.items.push(e.data);
              self.file1 = null;
              self.file2 = null;
              self.itemName = null;
            }
          }, error: function () {
            $('body').removeClass("loading");
            alert('トライアル範囲を超えました。担当者にご連絡お願い致します。')
          }
        });
        return true
      } else if (this.itemName == null) {
        this.error = true;
        $('#item-name').focus();
      }
      return false
    },
    startProcess: function () {
      let data = [this.pkgId];
      $('body').addClass('loading');
      this.socket.emit('process', {data: data});
    },
    submitFiles() {
      var formData = new FormData();
      for (let i in this.list) {
        formData.append("img_data[]", this.list[i].file);
        formData.append("type_img_" + i, this.list[i].type != null ? this.list[i].type : '');
        formData.append("name_" + i, this.list[i].name);
      }
      $('body').addClass("loading");
      $.ajax({
        url: "/upload",
        type: "POST",
        data: formData,
        mimeTypes: "multipart/form-data",
        contentType: false,
        processData: false,
        success: function () {
          $('body').removeClass("loading");
          window.location.replace('/history')
        }, error: function () {
          $('body').removeClass("loading");
          alert('トライアル範囲を超えました。担当者にご連絡お願い致します。')
        }
      });
    }
  }
});
myObject = new Vue({
  el: '#upload',
  data: {
    list: [],
    formats: null,
    default_type: null,
    files: null,
    editedTodo: null
  },
  beforeMount: function () {
    // this.formats = localData;
    if (this.formats != null && this.formats['sub_form'] && this.formats['sub_form'].length === 0) {
      this.default_type = this.formats.id;
    }
  },
  methods: {
    selectFile() {
      $('#files').click();
    },
    selectDefault(type) {
      this.default_type = type.id
    },
    fileDragHover(e) {
      var fileDrag = document.getElementById('upload-content');
      e.stopPropagation();
      e.preventDefault();
      fileDrag.className = (e.type === 'dragover' ? 'hover' : 'card-body');
    },
    deleteImg(index) {
      this.list.splice(index, 1);
    },
    fileDropHover(e) {
      var fileDrag = document.getElementById('upload-content');
      fileDrag.className = 'card-body';
      let droppedFiles = e.dataTransfer.files;
      if (!droppedFiles) return;
      ([...droppedFiles]).forEach(f => {
        if (f.type.match('image.*') || f.type.match('application/pdf')) {
          let data = {
            'file': f,
            'url': URL.createObjectURL(f),
            'type': this.default_type,
            'name': f.name,
            'edit': false
          };
          this.list.push(data);
        }
      });
    },
    editTodo: function (todo) {
      this.list = todo;
    },
    handleFilesUpload() {
      this.files = this.$refs.files.files;
      for (var i = 0; i < this.files.length; i++) {
        if (this.files[i].type.match('image.*') || this.files[i].type.match('application/pdf')) {
          let data = {
            'file': this.files[i],
            'url': URL.createObjectURL(this.files[i]),
            'type': this.default_type,
            'name': this.files[i].name,
            'edit': false
          };
          this.list.push(data);
        }
      }
    },
    clear() {
      this.list = [];
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
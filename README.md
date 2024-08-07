# lldb_scripts
[TOC]

## 1、自定义lldb命令

本文主要介绍如何自定义lldb命令，不涉及lldb中的调试（参考HelloLLDB工程）。

创建自定义lldb命令，主要有两种方式

* 创建简短命令
  * 主要是将较长的命令和参数，定义别名，方便快捷使用
  * 参考“LLDB commands”一节

* 创建python脚本，脚本提供命令
  * 主要通过脚本完成复杂的功能，比如下载pod库的源码，关联当前二进制文件等
  * 参考“LLDB scripts”一节



## 2、LLDB commands[^1]

### (1) ivars

ivars命令查看对象的实例变量

```shell
# Get all the ivars
(lldb) ivars <object>
```

配置代码，如下

```python
command regex ivars -h "Dumps all ivars for an instance of a particular class which inherits from NSObject (iOS, NSObject subclass only)" -s "ivars [UIView new]" -- 's/(.+)/expression -lobjc -O -- [%1 _ivarDescription]/'
```



### (2) methods/methods_r

methods命令查看对象的所有方法，methods_r命令查看对象的所有方法以及父类的所有方法

```shell
# Get all the methods of UIView
(lldb) methods UIView
```

配置代码，如下

```python
# methods
command regex methods -h "Dumps all methods implemented by the NSObject subclass (iOS, NSObject subclass only)" -s "methods UIView" -- 's/(.+)/expression -lobjc -O -- [%1 _shortMethodDescription]/'

# methods_r
command regex methods_r -h "Dumps all methods implemented by the NSObject subclass (iOS, NSObject subclass only)" -s "methods UIView" -- 's/(.+)/expression -lobjc -O -- [%1 _methodDescription]/'
```



### (3) pprotocol

打印某个协议的所有方法 (仅适用于Objective-C代码)

```shell
# Dump the protocol for UITableViewDataSource
(lldb) pprotocol UITableViewDataSource
```



配置代码，如下

```python
# pprotocol
command regex pprotocol 's/(.+)/expression -lobjc -O -- @import Foundation; NSMutableString *string = [NSMutableString string]; Protocol * prot = objc_getProtocol("%1"); [string appendFormat:@"\nProtocol: %s, %@\n", (char *)[prot name], (id)prot]; [string appendString:@"==========================================\n"]; for (int isRequired = 1; isRequired > -1; isRequired--) { [string appendFormat:@" (%@)\n", isRequired ? @"Required" : @"Optional"]; for (int isInstanceMethod = 0; isInstanceMethod < 2; isInstanceMethod++) { unsigned int ds_count = 0; struct objc_method_description * methods = (struct objc_method_description *)protocol_copyMethodDescriptionList(prot, (BOOL)isRequired, (BOOL)isInstanceMethod, &ds_count); for (int i = 0; i < ds_count; i++) { struct objc_method_description method = methods[i]; [string appendFormat:@"%@ %@, %s\n", isInstanceMethod ? @"-": @"+", NSStringFromSelector(method.name), method.types]; }}} string;/'
```



示例使用

```shell
(lldb) pprotocol UITableViewDataSource

Protocol: UITableViewDataSource, <Protocol: 0x7fff89e22458>
==========================================
 (Required)
- tableView:numberOfRowsInSection:, q32@0:8@16q24
- tableView:cellForRowAtIndexPath:, @32@0:8@16@24
 (Optional)
- tableView:titleForHeaderInSection:, @32@0:8@16q24
- tableView:commitEditingStyle:forRowAtIndexPath:, v40@0:8@16q24@32
- tableView:titleForFooterInSection:, @32@0:8@16q24
- numberOfSectionsInTableView:, q24@0:8@16
- tableView:canEditRowAtIndexPath:, B32@0:8@16@24
- tableView:canMoveRowAtIndexPath:, B32@0:8@16@24
- sectionIndexTitlesForTableView:, @24@0:8@16
- tableView:sectionForSectionIndexTitle:atIndex:, q40@0:8@16@24q32
- tableView:moveRowAtIndexPath:toIndexPath:, v40@0:8@16@24@32
```



### (4) tv

tv命令用于切换UIView对象的hidden状态

```shell
# Toggle a view on or off
(lldb) tv [UIView new]
```

配置代码，如下

```python
command regex -h "Toggle view. Hides/Shows a view depending on it's current state. You don't need to resume LLDB to see changes" -s "tv 0xUIViewAddress" -- tv 's/(.+)/expression -l objc -O -- @import QuartzCore; [%1 setHidden:!(BOOL)[%1 isHidden]]; (void)[CATransaction flush];/'
```



### (5) rlook

配置代码，如下

```python
# rlook
command regex -h "Regex search" -s "rlook UIViewController.viewDidLoad" -- rlook 's/(.+)/image lookup -rn %1/'
```



### (6) reload_lldbinit

当.lldbinit文件内容被修改，可以不用重新启动lldb，使用reload_lldbinit命令重新加载.lldbinit文件

配置代码，如下

```python
command alias -H "Reload ~/.lldbinit" -h "Reload ~/.lldbinit" -- reload_lldbinit command source ~/.lldbinit
```



### (7) args

读取方法Call Convention的1-6个参数，配置代码，如下

```python
command alias args register read arg1 arg2 arg3 arg4 arg5 arg6
```



### (8) python_version

打印python的版本[^3]。配置代码，如下

```python
# python_version
command alias -H "Check Python version" -h "Check Python version" -- python_version script import sys; print(sys.version)
```



### (9) pimage

打印UIImage的debug信息。配置代码，如下

```python
# pimage
command regex pimage 's/(.+)/expression -lobjc -O -- @import Foundation; NSMutableString *_debugInfoM_ = [NSMutableString string]; UIImage *_image_ = (UIImage *)%1; if ([_image_ isKindOfClass:[UIImage class]]) { NSString *_fileName_ = nil; NSString *_containerBundlePath_ = nil; if ([_image_ respondsToSelector:@selector(imageAsset)]) { UIImageAsset *imageAsset = _image_.imageAsset; _fileName_ = [imageAsset valueForKey:@"_assetName"]; _containerBundlePath_ = [imageAsset valueForKey:@"_containingBundle"]; } _debugInfoM_ = [[NSMutableString alloc] initWithFormat:@"<%@: %p> %@ %@ %@", [_image_ class], _image_, _fileName_, (id)NSStringFromCGSize(_image_.size), (NSString *)[_containerBundlePath_ bundlePath]]; } _debugInfoM_;/'
```



### (10) paddr

在Swift中打印内存地址[^4]。

配置代码，如下

```python
command regex paddr -h "Print memory address in Swift code" -s "paddr 0x123" -- 's/(.+)/expression -lswift -O -- unsafeBitCast(%1, to: NSObject.self)/'
```

或者

```python
command regex paddr -h "Print memory address in Swift code" -s "paddr 0x123" -- 's/(.+)/expression -lswift -O -- unsafeBitCast(%1, to: AnyObject.self)/'
```





// TODO

```
(lldb) visualize attrStringM
NSConcreteMutableAttributedString isn't supported. You can visualize UIImage, CGImageRef, UIView, CALayer, NSData, UIColor, CIColor, or CGColorRef.
```







## 3、LLDB scripts

### (1) write命令

```python
command script import ~/lldb_scripts/lldb_command_write.py
```



使用示例

```shell 
(lldb) write -h
```



### (2) ignore_specified_objc_exceptions命令

使用方法，如下

```
Usage:
1. place this script at ~/lldb
2. create an All Objective-C Exceptions breakpoint by Xcode
3. add a new Debugger Command, and type the formatted command

ignore_specified_objc_exceptions name:<exception name1> name:<exception name2> ...
```

> 代码见，ignore_specified_objc_exceptions.py



### (3) auto_add_dsym命令

自动关联本地的dSYM文件

思路：

* br设置main函数断点
* target stop-hook，获取当前image的uuid
* `mdfind "com_apple_xcode_dsym_uuids == 58028507-63B8-32C3-AD1C-9FDB2C8251DC"`，获取dSYM为路径
* 使用add-dsym设置dSYM
* 然后执行continue





## 4、配置`.lldbinit`文件

### (1) lldb_load_commands.py[^2]

`.lldbinit`文件位于`~/.lldbinit`，增加下面一行命令，如下

```shell
command script import ~/lldb_scripts/lldb_load_commands.py
```

lldb_load_commands.py的作用是批量加载lldb命令

* 读取lldb_commands.txt文件
* 同级目录下带前缀`lldb_command_`的python脚本

python脚本的内容，示例如下

```python
import lldb
import os


def __lldb_init_module(debugger, internal_dict):
    file_path = os.path.realpath(__file__)
    dir_name = os.path.dirname(file_path)
    load_python_scripts_dir(dir_name)


def load_python_scripts_dir(dir_name):
    this_files_basename = os.path.basename(__file__)
    cmd = ''
    for file in os.listdir(dir_name):
        if file.endswith('.py') and file.startswith('lldb_command_'):
            cmd = 'command script import '
        elif file.endswith('.txt'):
            cmd = 'command source -e0 -s1 '
        else:
            continue

        if file != this_files_basename:
            fullpath = dir_name + '/' + file
            lldb.debugger.HandleCommand(cmd + fullpath)
```

这里使用HandleCommand函数来执行command script或command source命令。



## 5、lldb模块

lldb提供一个名为lldb的python模块，该模块的API文档，见地址：https://lldb.llvm.org/python_reference/





## References

[^1]:https://github.com/DerekSelander/LLDB

[^2]:https://github.com/DerekSelander/LLDB/blob/master/lldb_commands/dslldb.py

[^3]:https://stackoverflow.com/questions/1093322/how-do-i-check-what-version-of-python-is-running-my-script

[^4]:https://stackoverflow.com/questions/29441418/lldb-swift-casting-raw-address-into-usable-type


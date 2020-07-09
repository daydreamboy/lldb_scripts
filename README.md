# lldb_scripts
[TOC]



## 1、LLDB commands[^1]

### （1）ivars

```python
command regex ivars -h "Dumps all ivars for an instance of a particular class which inherits from NSObject (iOS, NSObject subclass only)" -s "ivars [UIView new]" -- 's/(.+)/expression -lobjc -O -- [%1 _ivarDescription]/'
```



### （2）methods/methods_r

Dumps all methods inplemented by the NSObject subclass (iOS, NSObject subclass only)

```shell
# Get all the methods of UIView
(lldb) methods UIView
```





```python
command regex methods -h "Dumps all methods implemented by the NSObject subclass (iOS, NSObject subclass only)" -s "methods UIView" -- 's/(.+)/expression -lobjc -O -- [%1 _shortMethodDescription]/'
```





```python
command regex methods_r -h "Dumps all methods implemented by the NSObject subclass (iOS, NSObject subclass only)" -s "methods UIView" -- 's/(.+)/expression -lobjc -O -- [%1 _methodDescription]/'
```



### （3）pprotocol

Dumps all the required and optional methods for specific protocol (Objective-C only)

```shell
# Dump the protocol for UITableViewDataSource
(lldb) pprotocol UITableViewDataSource
```



code

```python
# pprotocol
command regex pprotocol 's/(.+)/expression -lobjc -O -- @import Foundation; NSMutableString *string = [NSMutableString string]; Protocol * prot = objc_getProtocol("%1"); [string appendFormat:@"\nProtocol: %s, %@\n", (char *)[prot name], (id)prot]; [string appendString:@"==========================================\n"]; for (int isRequired = 1; isRequired > -1; isRequired--) { [string appendFormat:@" (%@)\n", isRequired ? @"Required" : @"Optional"]; for (int isInstanceMethod = 0; isInstanceMethod < 2; isInstanceMethod++) { unsigned int ds_count = 0; struct objc_method_description * methods = (struct objc_method_description *)protocol_copyMethodDescriptionList(prot, (BOOL)isRequired, (BOOL)isInstanceMethod, &ds_count); for (int i = 0; i < ds_count; i++) { struct objc_method_description method = methods[i]; [string appendFormat:@"%@ %@, %s\n", isInstanceMethod ? @"-": @"+", NSStringFromSelector(method.name), method.types]; }}} string;/'
```



### （4）tv



```shell
# Toggle a view on or off
(lldb) tv [UIView new]
```



```python
command regex -h "Toggle view. Hides/Shows a view depending on it's current state. You don't need to resume LLDB to see changes" -s "tv 0xUIViewAddress" -- tv 's/(.+)/expression -l objc -O -- @import QuartzCore; [%1 setHidden:!(BOOL)[%1 isHidden]]; (void)[CATransaction flush];/'
```



### （5）rlook



```python
# rlook
command regex -h "Regex search" -s "rlook UIViewController.viewDidLoad" -- rlook 's/(.+)/image lookup -rn %1/'
```



### （6）reload_lldbinit



```python
command alias -H "Reload ~/.lldbinit" -h "Reload ~/.lldbinit" -- reload_lldbinit command source ~/.lldbinit
```







## 2、LLDB scripts



### （1）write命令

```python
command script import ~/lldb_scripts/lldb_command_write.py
```



使用示例

```shell 
(lldb) write -h
```





```python
command script import ~/GitHub_Projects/chisel/fblldb.py
```







## 附录

### 1、.lldbinit文件位置

```shell
~/.lldbinit
```



```python
## --- lldb commands --- ##
...
```





## References

[^1]:https://github.com/DerekSelander/LLDB

